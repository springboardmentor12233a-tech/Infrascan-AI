import hashlib
import io
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
from app.models.user import User
from app.schemas.image import ImageOut
from app.core.deps import get_current_user
from app.services.storage import storage
from app.services.preprocessing import assess_quality, enhance_image
from app.services.inference import classify_damage, generate_gradcam
from app.services.segmentation import segment_crack, extract_crack_geometry_and_boxes, draw_bounding_boxes, render_mask_png
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
            bounding_boxes=geom.get("bounding_boxes"),
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
    mode: str = Query("original", pattern="^(original|enhanced|gradcam|mask|boxes)$"),
    db: Session = Depends(get_db)
):
    """
    Stream either:
    - original: Raw uploaded image
    - enhanced: CLAHE + Gaussian denoising
    - gradcam: Activation heatmap (explainable AI)
    - mask: Segmentation mask overlay (crack boundary delineation)
    - boxes: Bounding boxes (defect localization)
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

    if mode == "enhanced":
        try:
            enhanced_bytes = enhance_image(content)
            return Response(content=enhanced_bytes, media_type="image/jpeg")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to enhance image: {str(e)}"
            )

    if mode == "gradcam":
        try:
            gradcam_bytes = generate_gradcam(content)
            return Response(content=gradcam_bytes, media_type="image/jpeg")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate Grad-CAM heatmap: {str(e)}"
            )

    if mode == "mask":
        try:
            _, overlay_rgb = segment_crack(content, has_crack=bool(image_record.has_crack))
            is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(overlay_rgb, cv2.COLOR_RGB2BGR))
            return Response(content=buffer.tobytes(), media_type="image/jpeg")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate crack segmentation mask: {str(e)}"
            )

    if mode == "boxes":
        try:
            boxes_bytes = draw_bounding_boxes(content, image_record.bounding_boxes or "[]")
            return Response(content=boxes_bytes, media_type="image/jpeg")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to draw bounding boxes: {str(e)}"
            )

    return Response(content=content, media_type=media_type)


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
            geom = extract_crack_geometry_and_boxes(mask, (img.height, img.width))
            img.crack_type = geom.get("crack_type")
            img.crack_length_px = geom.get("crack_length_px")
            img.max_crack_width_px = geom.get("max_crack_width_px")
            img.avg_crack_width_px = geom.get("avg_crack_width_px")
            img.crack_density_pct = geom.get("crack_density_pct")
            img.crack_area_px = geom.get("crack_area_px")
            img.bounding_boxes = geom.get("bounding_boxes")

            if img.has_crack:
                cracked_count += 1
            if severity_order.get(img.severity_level, 0) > severity_order.get(max_severity, 0):
                max_severity = img.severity_level

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

