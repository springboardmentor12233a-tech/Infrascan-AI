import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.models import ImageRecord, InfrastructureAsset, Inspection, User
from app.storage.local import LocalStorageBackend, validate_image_bytes

router = APIRouter(prefix="/images", tags=["Images"])
storage = LocalStorageBackend()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_image(
    asset_id: str = Form(...),
    inspection_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "Engineer", "Inspector")),
):
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not asset or not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset or inspection not found")
    if inspection.asset_id != asset.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inspection does not belong to asset")

    content = await file.read()
    width, height = validate_image_bytes(content, file.content_type or "")
    storage_key = storage.save_file(content, f"originals/{asset.id}", file.filename or "upload.jpg")

    record = ImageRecord(
        image_code=f"IMG-{uuid.uuid4().hex[:8].upper()}",
        asset_id=asset.id,
        inspection_id=inspection.id,
        original_filename=file.filename or "upload.jpg",
        stored_filename=storage_key.split("/")[-1],
        storage_path=storage_key,
        mime_type=file.content_type or "image/jpeg",
        file_size=len(content),
        image_width=width,
        image_height=height,
        uploaded_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "image_code": record.image_code,
        "original_filename": record.original_filename,
        "width": record.image_width,
        "height": record.image_height,
        "file_size": record.file_size,
    }


@router.get("")
def list_images(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ImageRecord).all()


@router.get("/{image_id}/file")
def get_image_file(image_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    path = storage.get_file_path(record.storage_path)
    return FileResponse(path, media_type=record.mime_type, filename=record.original_filename)

