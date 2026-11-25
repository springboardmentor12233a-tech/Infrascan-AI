"""Router for AI Model Registry and Crop Classification."""

import json
import logging
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.analysis import ModelVersion
from app.models.dataset import DatasetVersion, ModelEvent
from app.models.user import User
from app.schemas.model import (
    ClassifyCropResponse,
    DatasetVersionResponse,
    ModelEventResponse,
    ModelVersionResponse,
)
from app.services import model_registry
from app.services.audit import create_audit_log
from app.services.classifier_service import classify_crop
from app.services.event_service import publish

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Models"])


def _format_model_response(m: ModelVersion) -> Dict[str, Any]:
    class_names = json.loads(m.class_names_json) if m.class_names_json else None
    metrics = json.loads(m.metrics_json) if m.metrics_json else None
    return {
        "model_id": m.model_id,
        "model_name": m.model_name,
        "task": m.task,
        "version": m.version,
        "weights_path": m.weights_path,
        "threshold": m.threshold,
        "class_names": class_names,
        "metrics": metrics,
        "is_active": m.is_active,
        "inferences_count": m.inferences_count or 0,
        "mean_inference_time_ms": m.mean_inference_time_ms or 0.0,
        "last_inference_at": m.last_inference_at,
        "error_count": m.error_count or 0,
        "created_at": m.created_at,
    }


@router.get("/models/registry", response_model=List[ModelVersionResponse])
@router.get("/model-versions", response_model=List[ModelVersionResponse])
def list_models(
    task: Optional[str] = Query(None, description="Filter by task (detection, segmentation, classification)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all registered AI models with operational metrics."""
    # Ensure default models are seeded
    model_registry.seed_default_models(db)
    models = model_registry.get_all_models(db, task=task)
    return [_format_model_response(m) for m in models]


@router.get("/models/datasets", response_model=List[DatasetVersionResponse])
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List dataset versions and split statistics."""
    model_registry.seed_default_models(db)
    dss = db.query(DatasetVersion).order_by(DatasetVersion.id).all()
    res = []
    for d in dss:
        res.append({
            "id": d.id,
            "name": d.name,
            "version": d.version,
            "task": d.task,
            "split_stats": json.loads(d.split_stats_json) if d.split_stats_json else None,
            "created_at": d.created_at,
        })
    return res


@router.get("/models/{model_id}", response_model=ModelVersionResponse)
def get_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single model details."""
    m = model_registry.get_model_by_id(db, model_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")
    return _format_model_response(m)


@router.get("/models/{model_id}/events", response_model=List[ModelEventResponse])
def get_model_events(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get audit trail of model events (activation, rollback, smoke tests)."""
    events = db.query(ModelEvent).filter(ModelEvent.model_id == model_id).order_by(ModelEvent.created_at.desc()).all()
    res = []
    for e in events:
        res.append({
            "id": e.id,
            "model_id": e.model_id,
            "event_type": e.event_type,
            "performed_by": e.performed_by,
            "details": json.loads(e.details_json) if e.details_json else None,
            "created_at": e.created_at,
        })
    return res


@router.post("/models/{model_id}/activate", response_model=ModelVersionResponse)
def activate_model_endpoint(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Activate a model version after mandatory smoke test.
    Only accessible by Admin.
    """
    try:
        model = model_registry.activate_model(db, model_id, user_id=current_user.user_id)
        publish(
            db=db,
            event_type="model.activated",
            entity_type="model",
            entity_id=model_id,
            audience={"all": True},
            payload={
                "model_id": model_id,
                "model_name": model.model_name,
                "version": model.version,
            },
        )
        db.commit()
        create_audit_log(
            db=db,
            user_id=current_user.user_id,
            action="model_activated",
            entity_type="model_version",
            entity_id=model_id,
        )
        return _format_model_response(model)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except (RuntimeError, FileNotFoundError) as re:
        raise HTTPException(status_code=422, detail=f"Activation rejected: {str(re)}")


@router.post("/models/{model_id}/rollback", response_model=ModelVersionResponse)
def rollback_model_endpoint(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """
    Rollback an active model, restoring the previous version.
    Only accessible by Admin.
    """
    try:
        model = model_registry.rollback_model(db, model_id, user_id=current_user.user_id)
        create_audit_log(
            db=db,
            user_id=current_user.user_id,
            action="model_rollback",
            entity_type="model_version",
            entity_id=model_id,
        )
        return _format_model_response(model)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/classify-crop", response_model=ClassifyCropResponse)
@router.post("/models/classify-crop", response_model=ClassifyCropResponse)
async def classify_crop_endpoint(
    file: UploadFile = File(..., description="Crop image file (max 600x600 px)"),
    threshold: float = Form(0.50, description="Decision threshold"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Classify an image crop for crack presence using ResNet-50 trained on SDNET2018.
    Crop dimensions must be <= 600px; otherwise rejected with HTTP 422.
    Returns mandatory screening disclaimer.
    """
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    crop_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if crop_bgr is None:
        raise HTTPException(status_code=400, detail="Invalid image file. Could not decode.")

    h, w = crop_bgr.shape[:2]
    if max(h, w) > 600:
        raise HTTPException(
            status_code=422,
            detail=f"Crop dimension {w}x{h} exceeds maximum 600px limit. Please provide a tighter bounding crop around the candidate region.",
        )

    try:
        result = classify_crop(crop_bgr=crop_bgr, db=db, threshold=threshold)
        return result
    except Exception as e:
        logger.error(f"Error in classify_crop: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Crop classification failed: {str(e)}")
