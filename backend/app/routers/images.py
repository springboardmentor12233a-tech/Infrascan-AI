import hashlib
import io
import json
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
import cv2
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.inspection import Inspection
from app.models.inspection_image import InspectionImage, QualityStatus
from app.models.notification import Notification, AlertLevel
from app.models.user import User
from app.schemas.image import ImageOut
from app.core.deps import get_current_user
from app.services.storage import storage
from app.services.preprocessing import (
    assess_quality,
    enhance_image,
    sharpen_image,
    shadow_reduction,
    edge_enhancement,
    texture_enhancement,
    roi_extraction,
)
from app.services.inference import (
    classify_damage,
    generate_gradcam,
    generate_gradcam_plus_plus,
    generate_saliency_map,
)
from app.services.segmentation import (
    segment_crack,
    extract_crack_geometry_and_boxes,
    draw_bounding_boxes,
    render_mask_png,
    render_skeleton_overlay,
)
from app.services.damage_classifier import detect_multi_class_damage, compute_overall_risk_score
from app.services.audit import log_action

router = APIRouter(tags=["Images"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


@router.post("/inspections/{inspection_id}/images", response_model=List[ImageOut], status_code=status.HTTP_201_CREATED)
async def upload_inspection_images(
    inspection_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload multiple images for an inspection.
    Validates file extension, size, resolution, duplicate MD5, and runs quality checks.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found"
        )

    # Permission: Admin, Manager, or assigned Inspector
    role_name = current_user.role.name if current_user.role else ""
    if role_name not in ["Administrator", "Infrastructure Manager"]:
        if role_name == "Infrastructure Inspector" and inspection.inspector_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only upload images for your assigned inspections."
            )
        elif role_name not in ["Infrastructure Inspector"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role cannot upload images."
            )

    uploaded_records: List[InspectionImage] = []
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    for file in files:
        # 1. Extension validation
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '{ext}'. Allowed: .jpg, .jpeg, .png"
            )

        # Read content
        content = await file.read()
        file_size_kb = round(len(content) / 1024.0, 2)

        # 2. File size validation
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        # 3. MD5 calculation & Duplicate check within same inspection
        md5 = hashlib.md5(content).hexdigest()
        duplicate = db.query(InspectionImage).filter(
            InspectionImage.inspection_id == inspection_id,
            InspectionImage.md5_hash == md5
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate image detected: '{file.filename}' was already uploaded to this inspection."
            )

        # 4. Image readability and resolution validation
        try:
            with PILImage.open(io.BytesIO(content)) as pil_img:
                width, height = pil_img.size
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Corrupt or unreadable image: '{file.filename}'"
            )

        if width < settings.MIN_IMAGE_WIDTH or height < settings.MIN_IMAGE_HEIGHT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image resolution {width}x{height} too small. Minimum required: {settings.MIN_IMAGE_WIDTH}x{settings.MIN_IMAGE_HEIGHT}."
            )

        # 5. Quality assessment (blur & brightness)
        try:
            blur_score, brightness, quality_status_str = assess_quality(
                content,
                blur_threshold=settings.BLUR_THRESHOLD,
                brightness_threshold=settings.BRIGHTNESS_THRESHOLD
            )
            q_status = QualityStatus(quality_status_str)
        except Exception as e:
            blur_score, brightness, q_status = None, None, QualityStatus.OK

        # 6. Save with secure randomized filename
        safe_filename = f"{uuid.uuid4().hex}{ext}"
        storage.save_file(safe_filename, io.BytesIO(content))

        # 7. AI Crack & Damage Classification + Segmentation & Geometry
        damage_eval = classify_damage(content)
        has_crack = damage_eval.get("has_crack", False)

        mask, _ = segment_crack(content, has_crack=has_crack)
        geom = extract_crack_geometry_and_boxes(mask, (height, width))

        # Multi-class structural damage & overall risk score
        multi_damage = detect_multi_class_damage(
            content,
            has_crack=has_crack,
            crack_confidence=damage_eval.get("confidence_score") or 0.0
        )
        risk_info = compute_overall_risk_score(multi_damage)

        image_record = InspectionImage(
            inspection_id=inspection_id,
            file_path=safe_filename,
            original_filename=file.filename or safe_filename,
            md5_hash=md5,
            width=width,
            height=height,
            file_size_kb=file_size_kb,
            blur_score=blur_score,
            brightness=brightness,
            quality_status=q_status,
            has_crack=has_crack,
            confidence_score=damage_eval.get("confidence_score"),
            severity_level=damage_eval.get("severity_level"),
            crack_type=geom.get("crack_type"),
            crack_length_px=geom.get("crack_length_px"),
            max_crack_width_px=geom.get("max_crack_width_px"),
            avg_crack_width_px=geom.get("avg_crack_width_px"),
            crack_density_pct=geom.get("crack_density_pct"),
            crack_area_px=geom.get("crack_area_px"),
            crack_length_mm=geom.get("crack_length_mm"),
            max_crack_width_mm=geom.get("max_crack_width_mm"),
            avg_crack_width_mm=geom.get("avg_crack_width_mm"),
            crack_area_mm2=geom.get("crack_area_mm2"),
            orientation_deg=geom.get("orientation_deg"),
            branching_points=geom.get("branching_points"),
            calibration_mm_per_px=geom.get("calibration_mm_per_px", 0.2),
            bounding_boxes=geom.get("bounding_boxes"),
            damage_types=json.dumps(multi_damage),
            risk_score=float(risk_info["risk_score"]),
        )
        db.add(image_record)
        uploaded_records.append(image_record)

    db.commit()
    for rec in uploaded_records:
        db.refresh(rec)

    log_action(
        db,
        action="upload_images",
        entity="inspection",
        entity_id=str(inspection_id),
        user_id=current_user.id
    )

    # Return with public file URL
    results = []
    for rec in uploaded_records:
        data = ImageOut.model_validate(rec)
        data.url = f"/uploads/{rec.file_path}"
        results.append(data)
    return results


@router.get("/inspections/{inspection_id}/images", response_model=List[ImageOut])
def list_inspection_images(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all images associated with an inspection."""
    images = db.query(InspectionImage).filter(InspectionImage.inspection_id == inspection_id).all()
    results = []
    for img in images:
        data = ImageOut.model_validate(img)
        data.url = f"/uploads/{img.file_path}"
        results.append(data)
    return results


@router.get("/images/{image_id}/preview")
def preview_image(
    image_id: int,
    mode: str = Query("original", pattern="^(original|enhanced|sharpen|shadow_reduction|edge|texture|roi|gradcam|gradcam_plus|saliency|mask|skeleton|boxes)$"),
    db: Session = Depends(get_db)
):
    """
    Stream either:
    - original: Raw uploaded image
    - enhanced: CLAHE + Gaussian denoising
    - sharpen: Unsharp masking for fissure sharpening
    - shadow_reduction: Illumination normalization & shadow attenuation
    - edge: Canny & Sobel crack boundary edge contours
    - texture: Concrete aggregate roughness & spalling texture
    - roi: Central concrete surface region-of-interest isolation
    - gradcam: Activation heatmap (explainable AI)
    - gradcam_plus: Grad-CAM++ with higher-order gradient weighting
    - saliency: Pixel-level gradient saliency map
    - mask: Segmentation mask overlay
    - skeleton: Medial axis crack skeleton & junction nodes
    - boxes: Multi-defect localized bounding boxes
    """
    image_record = db.query(InspectionImage).filter(InspectionImage.id == image_id).first()
    if not image_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image record not found"
        )

    file_path = storage.get_file_path(image_record.file_path)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file missing from storage"
        )

    with open(file_path, "rb") as f:
        content = f.read()

    media_type = "image/jpeg" if file_path.lower().endswith((".jpg", ".jpeg")) else "image/png"

    try:
        if mode == "enhanced":
            return Response(content=enhance_image(content), media_type="image/jpeg")
        elif mode == "sharpen":
            return Response(content=sharpen_image(content), media_type="image/jpeg")
        elif mode == "shadow_reduction":
            return Response(content=shadow_reduction(content), media_type="image/jpeg")
        elif mode == "edge":
            return Response(content=edge_enhancement(content), media_type="image/jpeg")
        elif mode == "texture":
            return Response(content=texture_enhancement(content), media_type="image/jpeg")
        elif mode == "roi":
            return Response(content=roi_extraction(content), media_type="image/jpeg")
        elif mode == "gradcam":
            return Response(content=generate_gradcam(content), media_type="image/jpeg")
        elif mode == "gradcam_plus":
            return Response(content=generate_gradcam_plus_plus(content), media_type="image/jpeg")
        elif mode == "saliency":
            return Response(content=generate_saliency_map(content), media_type="image/jpeg")
        elif mode == "mask":
            _, overlay_rgb = segment_crack(content, has_crack=bool(image_record.has_crack))
            is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(overlay_rgb, cv2.COLOR_RGB2BGR))
            return Response(content=buffer.tobytes(), media_type="image/jpeg")
        elif mode == "skeleton":
            mask, _ = segment_crack(content, has_crack=bool(image_record.has_crack))
            return Response(content=render_skeleton_overlay(content, mask), media_type="image/jpeg")
        elif mode == "boxes":
            boxes_bytes = draw_bounding_boxes(content, image_record.bounding_boxes or "[]", image_record.damage_types)
            return Response(content=boxes_bytes, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render mode '{mode}': {str(e)}"
        )

    return Response(content=content, media_type=media_type)


@router.put("/images/{image_id}/calibration", response_model=ImageOut)
def update_image_calibration(
    image_id: int,
    calibration_mm_per_px: float = Query(..., gt=0.0, le=10.0, description="Real-world mm per pixel scale factor"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the pixel-to-real-world scale conversion ratio (mm/px) and recalculates
    physical dimensions (length, width, area in millimeters).
    """
    img = db.query(InspectionImage).filter(InspectionImage.id == image_id).first()
    if not img:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image record not found")

    img.calibration_mm_per_px = calibration_mm_per_px
    if img.crack_length_px:
        img.crack_length_mm = round(img.crack_length_px * calibration_mm_per_px, 2)
    if img.max_crack_width_px:
        img.max_crack_width_mm = round(img.max_crack_width_px * calibration_mm_per_px, 2)
    if img.avg_crack_width_px:
        img.avg_crack_width_mm = round(img.avg_crack_width_px * calibration_mm_per_px, 2)
    if img.crack_area_px:
        img.crack_area_mm2 = round(img.crack_area_px * (calibration_mm_per_px ** 2), 2)

    db.commit()
    db.refresh(img)
    data = ImageOut.model_validate(img)
    data.url = f"/uploads/{img.file_path}"
    return data


@router.post("/inspections/{inspection_id}/analyze")
def analyze_inspection_images(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Runs AI crack and damage assessment on all uploaded images in an inspection.
    Updates detection confidence and damage severity in the database.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found"
        )

    images = db.query(InspectionImage).filter(InspectionImage.inspection_id == inspection_id).all()
    if not images:
        return {
            "inspection_id": inspection_id,
            "total_images": 0,
            "cracked_count": 0,
            "max_severity": "None",
            "images": []
        }

    cracked_count = 0
    severity_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "None": 0}
    max_severity = "None"

    for img in images:
        file_path = storage.get_file_path(img.file_path)
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            eval_res = classify_damage(content)
            has_crack = eval_res.get("has_crack", False)
            img.has_crack = has_crack
            img.confidence_score = eval_res.get("confidence_score")
            img.severity_level = eval_res.get("severity_level")

            # Extract segmentation mask, bounding boxes & morphology measurements
            mask, _ = segment_crack(content, has_crack=has_crack)
            geom = extract_crack_geometry_and_boxes(
                mask,
                (img.height, img.width),
                calibration_mm_per_px=img.calibration_mm_per_px or 0.2
            )
            img.crack_type = geom.get("crack_type")
            img.crack_length_px = geom.get("crack_length_px")
            img.max_crack_width_px = geom.get("max_crack_width_px")
            img.avg_crack_width_px = geom.get("avg_crack_width_px")
            img.crack_density_pct = geom.get("crack_density_pct")
            img.crack_area_px = geom.get("crack_area_px")
            img.crack_length_mm = geom.get("crack_length_mm")
            img.max_crack_width_mm = geom.get("max_crack_width_mm")
            img.avg_crack_width_mm = geom.get("avg_crack_width_mm")
            img.crack_area_mm2 = geom.get("crack_area_mm2")
            img.orientation_deg = geom.get("orientation_deg")
            img.branching_points = geom.get("branching_points")
            img.bounding_boxes = geom.get("bounding_boxes")

            # Multi-class structural damage & overall risk score
            multi_damage = detect_multi_class_damage(
                content,
                has_crack=has_crack,
                crack_confidence=eval_res.get("confidence_score") or 0.0,
                crack_boxes=geom.get("boxes_list", [])
            )
            risk_info = compute_overall_risk_score(multi_damage)
            img.damage_types = json.dumps(multi_damage)
            img.risk_score = float(risk_info["risk_score"])

            if img.has_crack:
                cracked_count += 1
            if severity_order.get(img.severity_level, 0) > severity_order.get(max_severity, 0):
                max_severity = img.severity_level

    if max_severity in ["Critical", "High"]:
        asset_name = inspection.asset.name if inspection.asset else f"Asset #{inspection.asset_id}"
        db.add(Notification(
            target_role="Civil Engineer",
            title=f"High Risk Alert: {asset_name}",
            message=f"Inspection #{inspection_id} detected {max_severity} severity damage on {asset_name}. Engineering review recommended.",
            alert_level=AlertLevel.CRITICAL if max_severity == "Critical" else AlertLevel.HIGH,
            link=f"/inspections/{inspection_id}"
        ))

    db.commit()

    results = []
    for img in images:
        data = ImageOut.model_validate(img)
        data.url = f"/uploads/{img.file_path}"
        results.append(data)

    return {
        "inspection_id": inspection_id,
        "total_images": len(images),
        "cracked_count": cracked_count,
        "uncracked_count": len(images) - cracked_count,
        "max_severity": max_severity,
        "images": results
    }

