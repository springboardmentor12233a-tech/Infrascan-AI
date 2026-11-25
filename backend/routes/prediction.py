import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db, InspectionRecord
from backend.schemas.prediction import (
    ClassificationResponse,
    SegmentationResponse,
    CombinedPredictionResponse
)
from backend.services.classifier import classifier_service
from backend.services.damage_assessment import assess_damage
from backend.services.preprocessing import validate_and_decode_upload, save_uploaded_image
from backend.services.segmenter import segmenter_service

router = APIRouter(prefix="/predict", tags=["Prediction & Assessment"])


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    summary="Classify concrete crack presence",
    description="Accepts an image upload and predicts whether the concrete structure is Cracked or Uncracked."
)
async def predict_classification(file: UploadFile = File(...)):
    """Uploads concrete image and returns classification probability."""
    try:
        image_bgr, _ = await validate_and_decode_upload(file)
        result = classifier_service.predict(image_bgr)
        return ClassificationResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Classification inference failed: {str(exc)}")


@router.post(
    "/segment",
    response_model=SegmentationResponse,
    summary="Segment concrete cracks and generate overlay",
    description="Performs pixel-level U-Net segmentation, generates a binary crack mask and a transparent red crack overlay visualization."
)
async def predict_segmentation(request: Request, file: UploadFile = File(...)):
    """Uploads concrete image and returns segmentation mask & visual overlay."""
    try:
        image_bgr, _ = await validate_and_decode_upload(file)
        base_url = str(request.base_url)
        result = segmenter_service.predict(image_bgr, base_url=base_url)
        return SegmentationResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Segmentation inference failed: {str(exc)}")


@router.post(
    "",
    response_model=CombinedPredictionResponse,
    summary="Combined Crack Assessment (Classification + Segmentation + Damage)",
    description="Comprehensive assessment endpoint: provides classification confidence, pixel segmentation mask, crack coverage %, severity categorization, and persists inspection."
)
@router.post(
    "/",
    response_model=CombinedPredictionResponse,
    include_in_schema=False
)
async def predict_combined(
    request: Request,
    file: UploadFile = File(...),
    infrastructure_name: Optional[str] = Form(None),
    infrastructure_type: Optional[str] = Form(None),
    asset_id: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    inspector_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Executes full damage assessment pipeline and stores inspection record."""
    try:
        image_bgr, raw_bytes = await validate_and_decode_upload(file)
        base_url = str(request.base_url).rstrip("/")
        
        # Save original upload to static/uploads/
        orig_disk_path, orig_rel_path = save_uploaded_image(raw_bytes, file.filename or "uploaded_concrete.jpg")
        image_url = f"{base_url}/{orig_rel_path}"

        # 1. Classification
        cls_result = classifier_service.predict(image_bgr)

        # 2. Segmentation
        seg_result = segmenter_service.predict(image_bgr, base_url=base_url)

        # 3. Damage Assessment
        h, w = image_bgr.shape[:2]
        total_pixels = h * w
        is_cracked = cls_result["label"] == "Cracked" or seg_result["crack_pixel_count"] > 0
        damage_info = assess_damage(
            is_cracked=is_cracked,
            crack_pixels=seg_result["crack_pixel_count"],
            total_pixels=total_pixels,
            crack_percentage=seg_result["crack_percentage"],
            classification_confidence=cls_result["confidence"]
        )

        # 4. Formulate objective technical damage summary
        if is_cracked:
            summary = (
                f"Crack-like regions detected. Classification indicated crack patterns with {cls_result['confidence'] * 100:.2f}% confidence, "
                f"and segmentation localized {seg_result['crack_pixel_count']:,} crack-like pixels ({seg_result['crack_percentage']:.2f}% coverage). "
                f"Preliminary severity: {damage_info['severity_level']}. "
                "Further inspection by a qualified civil engineering professional is recommended."
            )
        else:
            summary = (
                f"No surface cracks detected. Classification assessed surface as uncracked with {cls_result['confidence'] * 100:.2f}% confidence, "
                "and segmentation detected 0 anomalous crack formations."
            )

        # 5. Persist to Database
        inspection_id = f"INFRASCAN-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        report_url = f"{base_url}/api/inspections/{inspection_id}/report"

        db_record = InspectionRecord(
            id=inspection_id,
            asset_id=asset_id or "",
            infrastructure_name=infrastructure_name or "Concrete Infrastructure",
            infrastructure_type=infrastructure_type or "Concrete Structure",
            location=location or "Site Alpha",
            inspector_name=inspector_name or "Lead Inspector",
            description=description or "",
            timestamp=datetime.utcnow(),
            filename=file.filename or "concrete_sample.jpg",
            image_path=orig_rel_path,
            classification_label=cls_result["label"],
            confidence=cls_result["confidence"],
            crack_probability=cls_result["crack_probability"],
            segmentation_label=seg_result["label"],
            crack_pixel_count=seg_result["crack_pixel_count"],
            total_pixels=total_pixels,
            crack_percentage=seg_result["crack_percentage"],
            severity_level=damage_info["severity_level"],
            suggested_priority=damage_info.get("suggested_priority", "Normal"),
            mask_path=seg_result["mask_path"],
            overlay_path=seg_result["overlay_path"],
            summary=summary
        )
        db.add(db_record)
        db.commit()

        return CombinedPredictionResponse(
            id=inspection_id,
            timestamp=db_record.timestamp.isoformat(),
            classification_label=cls_result["label"],
            confidence=cls_result["confidence"],
            crack_probability=cls_result["crack_probability"],
            segmentation_label=seg_result["label"],
            crack_pixel_count=seg_result["crack_pixel_count"],
            total_pixels=total_pixels,
            crack_percentage=seg_result["crack_percentage"],
            severity_level=damage_info["severity_level"],
            damage_assessment=damage_info,
            image_path=orig_rel_path,
            mask_path=seg_result["mask_path"],
            overlay_path=seg_result["overlay_path"],
            image_url=image_url,
            mask_url=seg_result["mask_url"],
            overlay_url=seg_result["overlay_url"],
            report_url=report_url,
            status="success",
            summary=summary
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Combined prediction pipeline failed: {str(exc)}")
