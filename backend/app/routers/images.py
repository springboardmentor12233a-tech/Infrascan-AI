from pathlib import Path
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.database import get_db
from app.deps import get_current_user
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.user import User
from app.schemas.image import ImageResponse, UploadBatchResponse
from app.services.audit import create_audit_log
from app.services.image_service import process_single_image
from app.services.preprocess_service import (
    process_image_preprocessing,
    run_preprocess_background,
)

router = APIRouter(tags=["Images"])


def resolve_image_disk_path(file_path_str: str) -> Path:
    """Resolve database relative path to absolute disk path."""
    p = Path(file_path_str)
    if not p.is_absolute():
        return BASE_DIR / p
    return p


# 1. POST /inspections/{id}/images - Batch upload images for an inspection
@router.post(
    "/inspections/{id}/images",
    response_model=UploadBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_inspection_images(
    id: int,
    request: Request,
    files: List[UploadFile],
    background_tasks: BackgroundTasks,
    source: str = Form("phone"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload one or multiple inspection photos with validation, EXIF parsing, and quality scoring.
    Allowed: assigned inspector, civil_engineer, or admin.
    Automatically advances inspection from 'assigned' to 'in_progress' upon first valid image.
    Automatically enqueues initial image preprocessing as a background task.
    """
    inspection = db.query(Inspection).filter(Inspection.inspection_id == id).first()
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found"
        )

    # Permission check: assigned inspector or civil_engineer or admin
    if current_user.role == "inspector":
        if inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inspectors can only upload photos to their own assigned inspections.",
            )
    elif current_user.role not in ["civil_engineer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to upload photos for this inspection.",
        )

    client_ip = request.client.host if request.client else None
    results = []
    accepted_count = 0
    warning_count = 0
    rejected_count = 0

    # Process each uploaded file independently (one bad file doesn't block others)
    for upload_file in files:
        file_bytes = await upload_file.read()
        filename = upload_file.filename or "unknown.jpg"

        result_item = process_single_image(
            file_bytes=file_bytes,
            original_filename=filename,
            inspection_id=id,
            user_id=current_user.user_id,
            source=source,
            db=db,
        )

        if result_item.status == "accepted":
            accepted_count += 1
            if result_item.image:
                create_audit_log(
                    db=db,
                    action="upload_image",
                    user_id=current_user.user_id,
                    entity_type="image",
                    entity_id=str(result_item.image.image_id),
                    ip_address=client_ip,
                )
                # Automatically run initial preprocessing in background
                background_tasks.add_task(
                    run_preprocess_background, result_item.image.image_id
                )
        elif result_item.status == "warning":
            warning_count += 1
            if result_item.image:
                create_audit_log(
                    db=db,
                    action="upload_image_warning",
                    user_id=current_user.user_id,
                    entity_type="image",
                    entity_id=str(result_item.image.image_id),
                    ip_address=client_ip,
                )
                # Automatically run initial preprocessing in background
                background_tasks.add_task(
                    run_preprocess_background, result_item.image.image_id
                )
        else:
            rejected_count += 1

        results.append(result_item)

    # When first image is saved and inspection is 'assigned', advance to 'in_progress'
    if (accepted_count > 0 or warning_count > 0) and inspection.status == "assigned":
        inspection.status = "in_progress"
        db.commit()
        db.refresh(inspection)
        create_audit_log(
            db=db,
            action="update_inspection_status",
            user_id=current_user.user_id,
            entity_type="inspection",
            entity_id=str(inspection.inspection_id),
            ip_address=client_ip,
        )

    return UploadBatchResponse(
        total_files=len(files),
        accepted_count=accepted_count,
        warning_count=warning_count,
        rejected_count=rejected_count,
        results=results,
    )


# 2. GET /inspections/{id}/images - List all image records for an inspection
@router.get("/inspections/{id}/images", response_model=List[ImageResponse])
def get_inspection_images(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List images for an inspection. Visibility adheres to inspection visibility rules."""
    inspection = db.query(Inspection).filter(Inspection.inspection_id == id).first()
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found"
        )

    # Inspectors only see images of inspections assigned to them
    if current_user.role == "inspector" and inspection.inspector_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view images for this inspection.",
        )

    images = (
        db.query(ImageModel)
        .filter(ImageModel.inspection_id == id)
        .order_by(ImageModel.uploaded_at.desc())
        .all()
    )
    return images


# 3. GET /images/{image_id} - Retrieve metadata for a single image
@router.get("/images/{image_id}", response_model=ImageResponse)
def get_image_metadata(
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve metadata and quality scores for an individual image."""
    image = db.query(ImageModel).filter(ImageModel.image_id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    # Check inspection visibility
    if current_user.role == "inspector":
        if image.inspection and image.inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this image metadata.",
            )

    return image


# 4. GET /images/{image_id}/file - Stream the authenticated image file
@router.get("/images/{image_id}/file")
def get_image_file(
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream image bytes securely. Requires authentication and matching role permissions."""
    image = db.query(ImageModel).filter(ImageModel.image_id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    # Visibility check
    if current_user.role == "inspector":
        if image.inspection and image.inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this image file.",
            )

    file_disk_path = resolve_image_disk_path(image.file_path)
    if not file_disk_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found on disk storage.",
        )

    media_type = "image/png" if file_disk_path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(
        path=str(file_disk_path),
        media_type=media_type,
        filename=image.original_filename,
    )


# 5. DELETE /images/{image_id} - Delete an image (DB + Disk)
@router.delete("/images/{image_id}")
def delete_image(
    image_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete image from database and disk storage.
    Allowed: admin, civil_engineer, or uploader while the inspection is not completed.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    inspection = image.inspection
    if inspection and inspection.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete photos from an inspection that has been completed.",
        )

    # Authorization: admin, civil_engineer, or the uploader
    is_admin_or_ce = current_user.role in ["admin", "civil_engineer"]
    is_uploader = image.uploaded_by == current_user.user_id

    if not (is_admin_or_ce or is_uploader):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this image.",
        )

    # Delete physical file from disk
    file_disk_path = resolve_image_disk_path(image.file_path)
    if file_disk_path.exists():
        try:
            file_disk_path.unlink()
        except Exception:
            pass

    # Also delete processed file from disk if present
    if image.processed_file_path:
        proc_disk_path = resolve_image_disk_path(image.processed_file_path)
        if proc_disk_path.exists():
            try:
                proc_disk_path.unlink()
            except Exception:
                pass

    client_ip = request.client.host if request.client else None

    # Delete record from database
    db.delete(image)
    db.commit()

    # Record audit log
    create_audit_log(
        db=db,
        action="delete_image",
        user_id=current_user.user_id,
        entity_type="image",
        entity_id=str(image_id),
        ip_address=client_ip,
    )

    return {"message": "Image deleted successfully"}


# 6. POST /images/{image_id}/preprocess - Re-run pipeline for a single image
@router.post("/images/{image_id}/preprocess", response_model=ImageResponse)
def trigger_single_image_preprocessing(
    image_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Re-run the preprocessing pipeline on a specific image.
    Allowed: admin, civil_engineer, or uploader.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == image_id).first()
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
            detail="You do not have permission to trigger preprocessing for this image.",
        )

    updated_image = process_image_preprocessing(db=db, image_id=image_id)
    if not updated_image:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute preprocessing on this image.",
        )

    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="preprocess_image",
        user_id=current_user.user_id,
        entity_type="image",
        entity_id=str(image_id),
        ip_address=client_ip,
    )

    return updated_image


# 7. GET /images/{image_id}/processed - Stream the enhanced/processed image file
@router.get("/images/{image_id}/processed")
def get_processed_image_file(
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Stream the processed image file.
    Requires authentication and adheres to the same inspection visibility rules as the original image.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    # Visibility check (same as original image)
    if current_user.role == "inspector":
        if image.inspection and image.inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this processed image file.",
            )

    if not image.processed_file_path or image.preprocess_status != "done":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processed image is not available or preprocessing has not completed.",
        )

    file_disk_path = resolve_image_disk_path(image.processed_file_path)
    if not file_disk_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processed image file not found on disk storage.",
        )

    return FileResponse(
        path=str(file_disk_path),
        media_type="image/jpeg",
        filename=f"processed_{image.original_filename}",
    )


# 8. POST /inspections/{id}/preprocess - Re-run pipeline for all images in an inspection
@router.post("/inspections/{id}/preprocess", response_model=List[ImageResponse])
def trigger_inspection_preprocessing(
    id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Re-run the preprocessing pipeline for all images associated with an inspection.
    Allowed: admin, civil_engineer.
    """
    if current_user.role not in ["admin", "civil_engineer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin and civil engineers can re-run preprocessing for an entire inspection.",
        )

    inspection = db.query(Inspection).filter(Inspection.inspection_id == id).first()
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found"
        )

    images = (
        db.query(ImageModel)
        .filter(ImageModel.inspection_id == id)
        .order_by(ImageModel.image_id.asc())
        .all()
    )

    results = []
    for img in images:
        updated = process_image_preprocessing(db=db, image_id=img.image_id)
        if updated:
            results.append(updated)

    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="preprocess_inspection",
        user_id=current_user.user_id,
        entity_type="inspection",
        entity_id=str(id),
        ip_address=client_ip,
    )

    return results
