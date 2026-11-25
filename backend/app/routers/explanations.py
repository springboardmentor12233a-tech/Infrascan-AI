"""API router for Explainable AI (XAI) attention maps and model comparisons.

Endpoints:
- POST /images/{id}/explain: Trigger explanation generation for an analyzed image.
- GET /images/{id}/explanations: Retrieve explanation records and metadata.
- GET /explanations/{id}/overlay: Stream authenticated JET colormap overlay PNG.
- GET /explanations/{id}/heatmap: Stream authenticated raw heatmap array (.npy or .png).
- POST /explanations/compare: Compare two attention maps (Spearman correlation & top 10% overlap).
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
import numpy as np
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.database import get_db
from app.deps import get_current_user
from app.models.analysis import AnalysisRun, run_models
from app.models.explanation import Explanation
from app.models.image import Image as ImageModel
from app.models.user import User
from app.schemas.explanation import (
    CompareMapsRequest,
    CompareMapsResponse,
    ExplainRequest,
    ExplanationResponse,
)
from app.services.analysis_service import resolve_disk_path
from app.services.audit import create_audit_log
from app.services.explain_service import (
    run_explanations_in_background,
    validate_model_method_pairs,
)
from app.ai.explain import compare_maps

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Explainable AI (XAI)"])


def _format_explanation_response(exp: Explanation) -> ExplanationResponse:
    """Format ORM model into Pydantic schema with parsed JSON fields and stream URLs."""
    params_dict = None
    if exp.params_json:
        try:
            params_dict = json.loads(exp.params_json)
        except Exception:
            pass

    warnings_list = []
    if exp.warnings_json:
        try:
            warnings_list = json.loads(exp.warnings_json)
        except Exception:
            pass

    overlay_url = f"/explanations/{exp.explanation_id}/overlay" if exp.overlay_path else None
    heatmap_url = f"/explanations/{exp.explanation_id}/heatmap" if exp.heatmap_path else None

    return ExplanationResponse(
        explanation_id=exp.explanation_id,
        run_id=exp.run_id,
        image_id=exp.image_id,
        model_id=exp.model_id,
        method=exp.method,
        target=exp.target,
        heatmap_path=exp.heatmap_path,
        overlay_path=exp.overlay_path,
        overlay_url=overlay_url,
        heatmap_url=heatmap_url,
        params=params_dict,
        warnings=warnings_list,
        seconds=exp.seconds,
        status=exp.status,
        error_message=exp.error_message,
        created_at=exp.created_at,
    )


# 1. POST /images/{id}/explain
@router.post(
    "/images/{id}/explain",
    response_model=List[ExplanationResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_image_explanation(
    id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    payload: Optional[ExplainRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger explanation generation (Grad-CAM, Grad-CAM++, Saliency, EigenCAM) for an analyzed image.
    Allowed roles: admin, civil_engineer, or the uploader.
    Requires a completed AI analysis run.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    # Permission check: admin, civil_engineer, or uploader
    is_admin_or_ce = current_user.role in ["admin", "civil_engineer"]
    is_uploader = image.uploaded_by == current_user.user_id
    if not (is_admin_or_ce or is_uploader):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to generate explanations for this image.",
        )

    # Check for completed analysis run
    latest_run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.image_id == id, AnalysisRun.status == "done")
        .order_by(AnalysisRun.run_id.desc())
        .first()
    )
    if not latest_run:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate explanations: no completed analysis run found for this image. Please run analysis first.",
        )

    # Retrieve models used in the run
    linked_models = (
        db.query(run_models.c.model_id)
        .filter(run_models.c.run_id == latest_run.run_id)
        .all()
    )
    run_model_ids = [m[0] for m in linked_models]
    if not run_model_ids:
        # Fallback to default detector and segmentation model
        run_model_ids = ["unetplusplus_crack500", "yolov8s_rdd2022"]

    det_configs = settings.get_detection_models()
    known_det_ids = [d.get("name") for d in det_configs] + [d.get("model_id") for d in det_configs]
    known_seg_ids = ["unetplusplus_crack500"]

    # Determine requested models and methods
    target_models = payload.models if (payload and payload.models) else run_model_ids
    target_methods = payload.methods if (payload and payload.methods) else None

    # Validate model-method pairs if explicit methods were passed
    if target_methods:
        try:
            validate_model_method_pairs(
                model_ids=target_models,
                methods=target_methods,
                detection_model_ids=known_det_ids,
                seg_model_ids=known_seg_ids,
            )
        except ValueError as val_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(val_err),
            )

    # Create pending explanation records
    created_records: List[Explanation] = []
    job_ids: List[int] = []

    for m_id in target_models:
        is_seg = m_id in known_seg_ids or "unet" in m_id.lower() or "seg" in m_id.lower()
        if target_methods:
            methods_for_model = list(target_methods)
        else:
            methods_for_model = ["gradcam", "gradcampp"] if is_seg else ["eigencam"]

        target_type = "mask" if is_seg else "detections"

        for meth in methods_for_model:
            exp_rec = Explanation(
                run_id=latest_run.run_id,
                image_id=image.image_id,
                model_id=m_id,
                method=meth,
                target=target_type,
                status="pending",
            )
            db.add(exp_rec)
            db.flush()
            created_records.append(exp_rec)
            job_ids.append(exp_rec.explanation_id)

    db.commit()

    # Enqueue background task
    background_tasks.add_task(
        run_explanations_in_background,
        explanation_ids=job_ids,
        image_id=image.image_id,
        run_id=latest_run.run_id,
    )

    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="generate_explanation",
        user_id=current_user.user_id,
        entity_type="image",
        entity_id=str(id),
        ip_address=client_ip,
    )

    return [_format_explanation_response(r) for r in created_records]


# 2. GET /images/{id}/explanations
@router.get(
    "/images/{id}/explanations",
    response_model=List[ExplanationResponse],
)
def get_image_explanations(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve all explanations for an image.
    Visibility matches image access permissions.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    # Visibility check: inspectors can only view assigned inspections
    if current_user.role == "inspector":
        if image.inspection and image.inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view explanations for this image.",
            )

    records = (
        db.query(Explanation)
        .filter(Explanation.image_id == id)
        .order_by(Explanation.explanation_id.desc())
        .all()
    )

    return [_format_explanation_response(r) for r in records]


# 3. GET /explanations/{id}/overlay
@router.get("/explanations/{id}/overlay")
def get_explanation_overlay(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Stream the generated JET colormap explanation overlay PNG.
    Requires authentication; visibility matches image access permissions. Never public static.
    """
    exp = db.query(Explanation).filter(Explanation.explanation_id == id).first()
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Explanation not found"
        )

    image = exp.image
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Associated image not found"
        )

    if current_user.role == "inspector":
        if image.inspection and image.inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this explanation overlay.",
            )

    if not exp.overlay_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Explanation overlay not found or generation failed.",
        )

    disk_path = resolve_disk_path(exp.overlay_path)
    if not disk_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Overlay file missing on disk.",
        )

    return FileResponse(
        path=str(disk_path),
        media_type="image/png",
        filename=disk_path.name,
    )


# 4. GET /explanations/{id}/heatmap
@router.get("/explanations/{id}/heatmap")
def get_explanation_heatmap(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Stream raw explanation heatmap array (.npy or .png).
    Requires authentication; visibility matches image access permissions. Never public static.
    """
    exp = db.query(Explanation).filter(Explanation.explanation_id == id).first()
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Explanation not found"
        )

    image = exp.image
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Associated image not found"
        )

    if current_user.role == "inspector":
        if image.inspection and image.inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this explanation heatmap.",
            )

    if not exp.heatmap_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Explanation heatmap not found or generation failed.",
        )

    disk_path = resolve_disk_path(exp.heatmap_path)
    if not disk_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heatmap file missing on disk.",
        )

    media_type = "application/x-numpy" if disk_path.suffix == ".npy" else "image/png"
    return FileResponse(
        path=str(disk_path),
        media_type=media_type,
        filename=disk_path.name,
    )


# 5. POST /explanations/compare
@router.post(
    "/explanations/compare",
    response_model=CompareMapsResponse,
)
def compare_explanation_maps(
    payload: CompareMapsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compare two generated attention maps, computing Spearman correlation and top 10% overlap.
    """
    exp_a = db.query(Explanation).filter(Explanation.explanation_id == payload.explanation_id_a).first()
    exp_b = db.query(Explanation).filter(Explanation.explanation_id == payload.explanation_id_b).first()

    if not exp_a or not exp_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both explanation IDs not found.",
        )

    for exp in (exp_a, exp_b):
        image = exp.image
        if current_user.role == "inspector":
            if image and image.inspection and image.inspection.inspector_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access one of the selected explanations.",
                )

    if not exp_a.heatmap_path or not exp_b.heatmap_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both explanations must have completed heatmaps available for comparison.",
        )

    path_a = resolve_disk_path(exp_a.heatmap_path)
    path_b = resolve_disk_path(exp_b.heatmap_path)

    if not path_a.exists() or not path_b.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Heatmap file missing on disk for comparison.",
        )

    map_a = np.load(str(path_a))
    map_b = np.load(str(path_b))

    stats = compare_maps(map_a, map_b)

    return CompareMapsResponse(
        explanation_id_a=exp_a.explanation_id,
        explanation_id_b=exp_b.explanation_id,
        spearman_correlation=stats["spearman_correlation"],
        top_10_overlap=stats["top_10_overlap"],
        interpretation=stats["interpretation"],
    )
