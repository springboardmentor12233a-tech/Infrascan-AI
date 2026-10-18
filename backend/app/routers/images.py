import hashlib
import io
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
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
            quality_status=q_status
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
    mode: str = Query("original", regex="^(original|enhanced)$"),
    db: Session = Depends(get_db)
):
    """
    Stream either the original or the enhanced (CLAHE + Gaussian denoise) image preview.
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

    return Response(content=content, media_type=media_type)
