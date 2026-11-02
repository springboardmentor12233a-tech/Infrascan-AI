"""Run and read AI analysis for an uploaded inspection image."""

import io
import json
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.ml.inference import analyze_image, model_status
from app.ml.preprocess import encode_jpeg, encode_png, read_upload
from app.models.image_analysis import ImageAnalysis
from app.models.inspection_image import InspectionImage
from app.models.user import User
from app.schemas.analysis import ImageAnalysisOut, ModelStatusOut
from app.services.audit import log_action
from app.services.storage import storage

router = APIRouter(tags=["Analysis"])

ANALYZE_ROLES = {
    "Administrator",
    "Infrastructure Manager",
    "Civil Engineer",
    "Infrastructure Inspector",
}


def _dumps(payload: object) -> str:
    return json.dumps(payload)


def _loads(payload: str) -> dict:
    return json.loads(payload) if payload else {}


def _to_out(record: ImageAnalysis, inspection_id: int) -> ImageAnalysisOut:
    overlay_url = f"/images/{record.image_id}/analysis/overlay" if record.overlay_path else None
    mask_url = f"/images/{record.image_id}/analysis/mask" if record.mask_path else None
    return ImageAnalysisOut(
        id=record.id,
        image_id=record.image_id,
        inspection_id=inspection_id,
        quality=_loads(record.quality_json),
        classification_status=record.classification_status,
        classification_label=record.classification_label,
        classification_confidence=record.classification_confidence,
        classification=_loads(record.classification_json),
        detection_status=record.detection_status,
        detection=_loads(record.detection_json),
        segmentation_status=record.segmentation_status,
        segmentation=_loads(record.segmentation_json),
        geometry=_loads(record.geometry_json),
        overlay_url=overlay_url,
        mask_url=mask_url,
        error_message=record.error_message,
        created_at=record.created_at,
    )


def _get_image(db: Session, image_id: int) -> InspectionImage:
    image = db.query(InspectionImage).filter(InspectionImage.id == image_id).first()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image record not found")
    return image


@router.get("/models/status", response_model=ModelStatusOut)
def get_model_status(current_user: User = Depends(get_current_user)):
    """Tell the client which weight files are actually on disk."""
    return model_status()


@router.get("/inspections/{inspection_id}/analyses", response_model=list[ImageAnalysisOut])
def list_analyses(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    images = db.query(InspectionImage).filter(InspectionImage.inspection_id == inspection_id).all()
    image_ids = {image.id: image for image in images}
    if not image_ids:
        return []
    records = db.query(ImageAnalysis).filter(ImageAnalysis.image_id.in_(image_ids)).all()
    return [_to_out(record, inspection_id) for record in records]


@router.get("/images/{image_id}/analysis", response_model=ImageAnalysisOut)
def get_analysis(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image = _get_image(db, image_id)
    record = db.query(ImageAnalysis).filter(ImageAnalysis.image_id == image_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This image has not been analyzed yet")
    return _to_out(record, image.inspection_id)


@router.post("/images/{image_id}/analyze", response_model=ImageAnalysisOut)
def analyze_inspection_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validate the stored image and run every model whose weights exist."""
    role_name = current_user.role.name if current_user.role else ""
    if role_name not in ANALYZE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot run analysis.")

    image = _get_image(db, image_id)
    file_path = storage.get_file_path(image.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file missing from storage")

    with open(file_path, "rb") as handle:
        content = handle.read()
    try:
        image_bgr = read_upload(content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    result = analyze_image(image_bgr)
    errors = [
        block.get("detail")
        for block in (result["classification"], result["detection"], result["segmentation"])
        if block.get("status") == "failed"
    ]

    mask_name = f"analysis_{image_id}_mask.png"
    overlay_name = f"analysis_{image_id}_overlay.jpg"
    mask = result["mask"]
    if mask is not None:
        storage.save_file(mask_name, io.BytesIO(encode_png(mask)))
    else:
        storage.delete_file(mask_name)
        mask_name = None
    storage.save_file(overlay_name, io.BytesIO(encode_jpeg(result["overlay_bgr"])))

    classification = result["classification"]
    detection = result["detection"]
    segmentation = result["segmentation"]
    record = db.query(ImageAnalysis).filter(ImageAnalysis.image_id == image_id).first()
    if record is None:
        record = ImageAnalysis(image_id=image_id)
        db.add(record)

    record.quality_json = _dumps(result["quality"])
    record.classification_status = classification["status"]
    record.classification_label = classification.get("label")
    record.classification_confidence = classification.get("confidence")
    record.classification_json = _dumps(classification)
    record.detection_status = detection["status"]
    record.detection_json = _dumps(detection)
    record.segmentation_status = segmentation["status"]
    record.segmentation_json = _dumps(segmentation)
    record.mask_path = mask_name
    record.overlay_path = overlay_name
    record.geometry_json = _dumps(result["geometry"])
    record.error_message = "; ".join(errors) if errors else None
    db.commit()
    db.refresh(record)

    log_action(
        db,
        action="analyze_image",
        entity="inspection_image",
        entity_id=str(image_id),
        user_id=current_user.id,
    )
    return _to_out(record, image.inspection_id)


def _render_artifact(image_id: int, kind: str, db: Session) -> Response:
    record = db.query(ImageAnalysis).filter(ImageAnalysis.image_id == image_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This image has not been analyzed yet")
    filename = record.overlay_path if kind == "overlay" else record.mask_path
    if not filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No {kind} was produced for this image")
    path = storage.get_file_path(filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{kind} file is missing from storage")
    with open(path, "rb") as handle:
        content = handle.read()
    media = "image/png" if kind == "mask" else "image/jpeg"
    return Response(content=content, media_type=media)


@router.get("/images/{image_id}/analysis/overlay")
def get_overlay(image_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _render_artifact(image_id, "overlay", db)


@router.get("/images/{image_id}/analysis/mask")
def get_mask(image_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _render_artifact(image_id, "mask", db)
