"""API router for AI analysis operations.

Endpoints:
- POST /images/{id}/analyze: Enqueue AI analysis for an uploaded image.
- POST /inspections/{id}/analyze: Enqueue AI analysis for all valid images in an inspection.
- GET /images/{id}/analysis: Retrieve the latest analysis run, detections, and geometry measurements.
- GET /analysis/{run_id}/mask: Stream authenticated mask PNG file.
"""

import logging
import math
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.database import SessionLocal, get_db
from app.deps import get_current_user
from app.models.analysis import AnalysisRun, CrackMeasurement, Detection, ImageScale, ModelVersion, run_models
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.user import User
from app.schemas.analysis import (
    AnalysisRunResponse,
    AnalyzeBatchResponse,
    AnalyzeImageRequest,
    CrackMeasurementResponse,
    DetectionResponse,
    DetectorInfoResponse,
    ImageScaleResponse,
    SetScaleRequest,
)
from app.services.analysis_service import execute_image_analysis, resolve_disk_path
from app.services.audit import create_audit_log
from app.services.event_service import publish

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Analysis"])


def run_analysis_in_background(
    run_id: int,
    image_id: int,
    mm_per_pixel: Optional[float],
    override_detectors: Optional[List[str]] = None,
):
    """Background worker for detached analysis execution."""
    db: Session = SessionLocal()
    try:
        execute_image_analysis(
            run_id=run_id,
            image_id=image_id,
            db=db,
            mm_per_pixel=mm_per_pixel,
            override_detectors=override_detectors,
        )
    except Exception as e:
        logger.error(f"Error running analysis in background: {e}", exc_info=True)
    finally:
        db.close()


def _format_run_response(run: AnalysisRun, db: Session) -> AnalysisRunResponse:
    """Format an AnalysisRun ORM object into the AnalysisRunResponse schema."""
    # Retrieve linked model IDs from junction table
    linked_models = (
        db.query(run_models.c.model_id)
        .filter(run_models.c.run_id == run.run_id)
        .all()
    )
    model_ids = [m[0] for m in linked_models]

    detections = [
        DetectionResponse.model_validate(d) for d in run.detections
    ]
    measurements = [
        CrackMeasurementResponse.model_validate(m) for m in run.crack_measurements
    ]

    return AnalysisRunResponse(
        run_id=run.run_id,
        image_id=run.image_id,
        status=run.status,
        error_message=run.error_message,
        started_at=run.started_at,
        finished_at=run.finished_at,
        seconds=run.seconds,
        image_scale_note=run.image_scale_note,
        detections=detections,
        crack_measurements=measurements,
        model_ids=model_ids,
    )


# 1. POST /images/{id}/analyze
@router.post(
    "/images/{id}/analyze",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def analyze_image(
    id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    payload: Optional[AnalyzeImageRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger AI analysis (distress detection + crack segmentation + geometry) for an image.
    Allowed roles: admin, civil_engineer, or the uploader.
    Enqueued via BackgroundTasks.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    # Permission check: admin, civil_engineer, or the uploader
    is_admin_or_ce = current_user.role in ["admin", "civil_engineer"]
    is_uploader = image.uploaded_by == current_user.user_id
    if not (is_admin_or_ce or is_uploader):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to run analysis on this image.",
        )

    if image.quality_status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot analyze image because quality_status is 'rejected'.",
        )

    override_detectors = payload.detectors if payload else None
    if override_detectors is not None:
        if not is_admin_or_ce:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin or civil_engineer can specify detector overrides.",
            )

    mm_per_pixel = payload.mm_per_pixel if payload else None

    # Create pending run record
    run = AnalysisRun(
        image_id=image.image_id,
        status="pending",
    )
    db.add(run)
    publish(
        db=db,
        event_type="analysis.queued",
        entity_type="analysis",
        entity_id=run.run_id,
        audience={"all": True},
        payload={"run_id": run.run_id, "image_id": image.image_id},
    )
    db.commit()
    db.refresh(run)

    # Enqueue background task
    background_tasks.add_task(
        run_analysis_in_background,
        run_id=run.run_id,
        image_id=image.image_id,
        mm_per_pixel=mm_per_pixel,
        override_detectors=override_detectors,
    )

    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="run_analysis",
        user_id=current_user.user_id,
        entity_type="image",
        entity_id=str(image.image_id),
        ip_address=client_ip,
    )

    return _format_run_response(run, db)


# 2. POST /inspections/{id}/analyze
@router.post(
    "/inspections/{id}/analyze",
    response_model=AnalyzeBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def analyze_inspection_images(
    id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    payload: Optional[AnalyzeImageRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger AI analysis on all valid (non-rejected) images in an inspection.
    Allowed roles: admin, civil_engineer.
    """
    if current_user.role not in ["admin", "civil_engineer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or civil_engineer can run batch inspection analysis.",
        )

    inspection = db.query(Inspection).filter(Inspection.inspection_id == id).first()
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found"
        )

    valid_images = [img for img in inspection.images if img.quality_status != "rejected"]
    if not valid_images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid (non-rejected) images available to analyze in this inspection.",
        )

    mm_per_pixel = payload.mm_per_pixel if payload else None
    override_detectors = payload.detectors if payload else None
    run_ids: List[int] = []

    for img in valid_images:
        run = AnalysisRun(
            image_id=img.image_id,
            status="pending",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        run_ids.append(run.run_id)
        background_tasks.add_task(
            run_analysis_in_background,
            run_id=run.run_id,
            image_id=img.image_id,
            mm_per_pixel=mm_per_pixel,
            override_detectors=override_detectors,
        )

    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="run_analysis",
        user_id=current_user.user_id,
        entity_type="inspection",
        entity_id=str(id),
        ip_address=client_ip,
    )

    return AnalyzeBatchResponse(
        enqueued_count=len(run_ids),
        run_ids=run_ids,
        message=f"Enqueued {len(run_ids)} images for AI analysis in inspection #{id}.",
    )


# 3. GET /images/{id}/analysis
@router.get(
    "/images/{id}/analysis",
    response_model=AnalysisRunResponse,
)
def get_image_latest_analysis(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve the latest AI analysis results for an image (detections and crack measurements).
    Visibility rules match image visibility.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    # Visibility check: inspector can only see images in inspections assigned to them
    if current_user.role == "inspector":
        if image.inspection and image.inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view analysis for this image.",
            )

    latest_run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.image_id == id)
        .order_by(AnalysisRun.run_id.desc())
        .first()
    )
    if not latest_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analysis run found for this image.",
        )

    return _format_run_response(latest_run, db)


# 4. GET /analysis/{run_id}/mask
@router.get(
    "/analysis/{run_id}/mask",
)
def get_analysis_mask(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Stream the generated binary crack segmentation mask PNG.
    Requires authentication; visibility matches image access permissions. Never public static.
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found"
        )

    image = run.image
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found for this run"
        )

    # Visibility check
    if current_user.role == "inspector":
        if image.inspection and image.inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this analysis mask.",
            )

    measurement = (
        db.query(CrackMeasurement)
        .filter(CrackMeasurement.run_id == run_id)
        .first()
    )
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No segmentation mask found for this analysis run.",
        )

    mask_disk_path = resolve_disk_path(measurement.mask_path)
    if not mask_disk_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mask image file not found on disk storage.",
        )

    return FileResponse(
        path=str(mask_disk_path),
        media_type="image/png",
        filename=f"mask_run_{run_id}.png",
    )


def _apply_scale_to_image_measurements(image_id: int, scale: Optional[ImageScale], db: Session):
    """
    Apply or clear scale on all crack measurements for an image.
    Uses exact Milestone 3 measurement rules:
    - length_mm = length_px x mm_per_pixel
    - width_mm = width_px x mm_per_pixel
    - method_error_mm = mm_per_pixel x 1.0 (1 px method error)
    - width_mm_uncertainty = sqrt((method_error_mm)^2 + (avg_width_mm x uncertainty_percent/100)^2)
    - length_mm_uncertainty = (length_mm x uncertainty_percent/100) + method_error_mm
    - perspective not corrected note when camera_perpendicular is False
    """
    runs = db.query(AnalysisRun).filter(AnalysisRun.image_id == image_id).all()
    for run in runs:
        for m in run.crack_measurements:
            if not scale or scale.mm_per_pixel is None or scale.mm_per_pixel <= 0:
                m.mm_per_pixel = None
                m.length_mm = None
                m.avg_width_mm = None
                m.max_width_mm = None
                m.length_mm_uncertainty = None
                m.width_mm_uncertainty = None
                m.scale_id = None
                m.measurement_note = None
            else:
                s_ratio = scale.mm_per_pixel
                u_ratio = (scale.uncertainty_percent or 0.0) / 100.0

                m.scale_id = scale.scale_id
                m.mm_per_pixel = s_ratio
                m.length_mm = round(m.length_px * s_ratio, 2)
                m.avg_width_mm = round(m.avg_width_px * s_ratio, 2)
                m.max_width_mm = round(m.max_width_px * s_ratio, 2)

                method_error_mm = s_ratio * 1.0
                width_unc = math.sqrt((method_error_mm) ** 2 + (m.avg_width_mm * u_ratio) ** 2)
                m.width_mm_uncertainty = round(width_unc, 2)

                length_unc = (m.length_mm * u_ratio) + method_error_mm
                m.length_mm_uncertainty = round(length_unc, 2)

                if not scale.camera_perpendicular:
                    m.measurement_note = "perspective not corrected: approximate"
                else:
                    m.measurement_note = None
    db.commit()


@router.put(
    "/images/{id}/scale",
    response_model=ImageScaleResponse,
    status_code=status.HTTP_200_OK,
)
def set_image_scale(
    id: int,
    payload: SetScaleRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Configure physical metric scale (mm per pixel) for an uploaded image.
    Allowed roles: admin, civil_engineer, or uploader.
    Body can be {mm_per_pixel} or {reference_mm, point1, point2}; plus camera_perpendicular.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    is_admin_or_ce = current_user.role in ["admin", "civil_engineer"]
    is_uploader = image.uploaded_by == current_user.user_id
    if not (is_admin_or_ce or is_uploader):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to configure scale for this image.",
        )

    ref_mm = payload.reference_mm
    p1 = payload.point1
    p2 = payload.point2
    p1x = payload.point1_x if payload.point1_x is not None else (p1[0] if p1 and len(p1) >= 2 else None)
    p1y = payload.point1_y if payload.point1_y is not None else (p1[1] if p1 and len(p1) >= 2 else None)
    p2x = payload.point2_x if payload.point2_x is not None else (p2[0] if p2 and len(p2) >= 2 else None)
    p2y = payload.point2_y if payload.point2_y is not None else (p2[1] if p2 and len(p2) >= 2 else None)

    if p1x is not None and p1y is not None and p2x is not None and p2y is not None and ref_mm is not None:
        method = "reference_object"
        if ref_mm <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference measurement in mm must be positive.",
            )
        pixel_distance = math.hypot(p2x - p1x, p2y - p1y)
        if pixel_distance < 100.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Reference object must be at least 100 pixels long (measured {pixel_distance:.1f} px). A short reference gives a large error.",
            )
        computed_scale = ref_mm / pixel_distance
        if not (0.01 <= computed_scale <= 20.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Computed scale ({computed_scale:.4f} mm/px) is outside valid range [0.01, 20.0] mm/px.",
            )
        ref_px = round(pixel_distance, 2)
        # uncertainty_percent = 100 x sqrt(2) / reference_px (a +-1 pixel error at each end point)
        uncertainty_percent = round(100.0 * math.sqrt(2) / pixel_distance, 4)
        mm_per_pixel = computed_scale
    elif payload.mm_per_pixel is not None:
        method = "manual_ratio"
        mm_per_pixel = payload.mm_per_pixel
        if mm_per_pixel <= 0 or not (0.01 <= mm_per_pixel <= 20.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scale mm_per_pixel must be between 0.01 and 20.0 (received {mm_per_pixel}).",
            )
        ref_mm = None
        ref_px = None
        p1x, p1y, p2x, p2y = None, None, None, None
        uncertainty_percent = 0.0
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either mm_per_pixel or (reference_mm and 2 reference points) must be provided.",
        )

    # Deactivate existing current scale for this image (keep old row with is_current=False)
    db.query(ImageScale).filter(
        ImageScale.image_id == image.image_id,
        ImageScale.is_current == True,
    ).update({"is_current": False})

    new_scale = ImageScale(
        image_id=image.image_id,
        method=method,
        mm_per_pixel=round(mm_per_pixel, 6),
        reference_mm=ref_mm,
        reference_px=ref_px,
        point1_x=p1x,
        point1_y=p1y,
        point2_x=p2x,
        point2_y=p2y,
        camera_perpendicular=payload.camera_perpendicular,
        uncertainty_percent=uncertainty_percent,
        is_current=True,
        set_by=current_user.user_id,
    )
    db.add(new_scale)
    db.commit()
    db.refresh(new_scale)

    # Automatically recompute existing measurements
    _apply_scale_to_image_measurements(image_id=image.image_id, scale=new_scale, db=db)

    create_audit_log(
        db=db,
        user_id=current_user.user_id,
        action="SET_SCALE",
        entity_type="image",
        entity_id=str(image.image_id),
        ip_address=request.client.host if request.client else None,
    )

    return ImageScaleResponse.model_validate(new_scale)


@router.get(
    "/images/{id}/scale",
    response_model=ImageScaleResponse,
    status_code=status.HTTP_200_OK,
)
def get_image_scale(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the current active scale configuration for an image."""
    image = db.query(ImageModel).filter(ImageModel.image_id == id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )
    scale = (
        db.query(ImageScale)
        .filter(ImageScale.image_id == id, ImageScale.is_current == True)
        .first()
    )
    if not scale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active scale configured for image #{id}.",
        )
    return ImageScaleResponse.model_validate(scale)


@router.delete(
    "/images/{id}/scale",
    status_code=status.HTTP_200_OK,
)
def delete_image_scale(
    id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove current scale configuration for an image.
    Deactivates the scale and clears calculated metric measurements.
    Allowed roles: admin, civil_engineer, or uploader.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )
    is_admin_or_ce = current_user.role in ["admin", "civil_engineer"]
    is_uploader = image.uploaded_by == current_user.user_id
    if not (is_admin_or_ce or is_uploader):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete scale for this image.",
        )

    scales = (
        db.query(ImageScale)
        .filter(ImageScale.image_id == id, ImageScale.is_current == True)
        .all()
    )
    for s in scales:
        s.is_current = False

    _apply_scale_to_image_measurements(image_id=id, scale=None, db=db)
    db.commit()

    create_audit_log(
        db=db,
        user_id=current_user.user_id,
        action="DELETE_SCALE",
        entity_type="image",
        entity_id=str(id),
        ip_address=request.client.host if request.client else None,
    )

    return {"message": f"Scale configuration cleared for image #{id}."}


@router.post(
    "/images/{id}/remeasure",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_200_OK,
)
def remeasure_image(
    id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Recompute the mm fields from the SAVED mask without running any model.
    Allowed roles: admin, civil_engineer, or uploader.
    If no scale: the mm fields stay null.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )
    is_admin_or_ce = current_user.role in ["admin", "civil_engineer"]
    is_uploader = image.uploaded_by == current_user.user_id
    if not (is_admin_or_ce or is_uploader):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to remeasure this image.",
        )

    run = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.image_id == id, AnalysisRun.status == "done")
        .order_by(AnalysisRun.run_id.desc())
        .first()
    )
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed analysis run found for image #{id}. Run analysis first.",
        )

    scale = (
        db.query(ImageScale)
        .filter(ImageScale.image_id == id, ImageScale.is_current == True)
        .first()
    )

    _apply_scale_to_image_measurements(image_id=id, scale=scale, db=db)

    create_audit_log(
        db=db,
        user_id=current_user.user_id,
        action="REMEASURE",
        entity_type="image",
        entity_id=str(id),
        ip_address=request.client.host if request.client else None,
    )

    db.refresh(run)
    return _format_run_response(run, db)


# 8. GET /models - List registered detectors with validation metrics and applicability
@router.get(
    "/models",
    response_model=List[DetectorInfoResponse],
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/analysis/models",
    response_model=List[DetectorInfoResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_registered_detectors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return registered detectors with name, classes, conf, imgsz, applicable_asset_types,
    domain_note, and validation metrics. Accessible to any logged-in user.
    """
    import json
    result = []
    detectors = settings.get_detection_models()

    for det in detectors:
        name = det.get("name") or det.get("model_id")
        raw_classes = det.get("class_names", [])
        if isinstance(raw_classes, dict):
            classes = [str(v) for v in raw_classes.values()]
        elif isinstance(raw_classes, (list, tuple)):
            classes = [str(c) for c in raw_classes]
        else:
            classes = []

        conf = float(det.get("conf", det.get("confidence", settings.YOLO_CONF)))
        imgsz = int(det.get("imgsz", 640))
        app_types = list(det.get("applicable_asset_types", []))
        domain_note = str(det.get("domain_note", ""))

        # Look up validation metrics from db or json files
        val_metrics = None
        mv = db.query(ModelVersion).filter(ModelVersion.model_id == name).first()
        if mv and mv.metrics_json:
            try:
                val_metrics = json.loads(mv.metrics_json)
            except Exception:
                pass

        if val_metrics is None:
            # Fallback to run_card / model_registry
            if name == "A2_rtdetr_l":
                reg_candidates = [
                    settings.ml_models_path / "models" / "detection_codebrim" / "model_registry.json",
                    BASE_DIR.parent / "ml" / "models" / "detection_codebrim" / "model_registry.json",
                ]
                for reg_path in reg_candidates:
                    if reg_path.exists():
                        try:
                            with open(reg_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            val_metrics = {"VALIDATION": data.get("validation_metrics", {})}
                            break
                        except Exception:
                            pass
            elif name == "yolov8s_rdd2022":
                card_candidates = [
                    settings.ml_models_path / "detection" / "yolov8s_rdd2022" / "run_card.json",
                    BASE_DIR.parent / "ml" / "detection" / "yolov8s_rdd2022" / "run_card.json",
                ]
                for card_path in card_candidates:
                    if card_path.exists():
                        try:
                            with open(card_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            val_metrics = data.get("metrics")
                            break
                        except Exception:
                            pass

        result.append(
            DetectorInfoResponse(
                name=name,
                classes=classes,
                conf=conf,
                imgsz=imgsz,
                applicable_asset_types=app_types,
                domain_note=domain_note,
                validation_metrics=val_metrics,
            )
        )

    return result

