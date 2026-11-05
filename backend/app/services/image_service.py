from datetime import datetime
import hashlib
import io
from pathlib import Path
from typing import Optional, Tuple
import uuid

from fastapi import UploadFile
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.ai.quality import assess_image_quality
from app.config import settings
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.schemas.image import ImageResponse, UploadResultItem

ALLOWED_IMAGE_FORMATS = {"JPEG": "jpg", "PNG": "png", "JPG": "jpg"}


def parse_gps_and_time(
    img: Image.Image,
) -> Tuple[Optional[float], Optional[float], Optional[datetime]]:
    """
    Extract GPS latitude/longitude and original capture time from EXIF metadata.
    Converts DMS tuples to signed decimal degrees (South/West negative).
    Returns (latitude, longitude, captured_at). Never raises exceptions on malformed EXIF.
    """
    lat: Optional[float] = None
    lon: Optional[float] = None
    captured_at: Optional[datetime] = None

    try:
        exif = img.getexif()
        if not exif:
            return None, None, None

        # 1. Capture Time (DateTimeOriginal 0x9003 or DateTime 0x0132)
        dt_str = exif.get(0x9003) or exif.get(0x0132)
        if dt_str and isinstance(dt_str, str):
            try:
                captured_at = datetime.strptime(dt_str.strip(), "%Y:%m:%d %H:%M:%S")
            except Exception:
                pass

        # 2. GPS Info IFD (Tag 0x8825)
        gps_ifd = exif.get_ifd(0x8825)
        if gps_ifd:
            lat_ref = gps_ifd.get(1)  # 'N' or 'S'
            lat_raw = gps_ifd.get(2)  # (deg, min, sec)
            lon_ref = gps_ifd.get(3)  # 'E' or 'W'
            lon_raw = gps_ifd.get(4)  # (deg, min, sec)

            def dms_to_decimal(dms):
                if dms and len(dms) >= 3:
                    d = float(dms[0])
                    m = float(dms[1])
                    s = float(dms[2])
                    return d + (m / 60.0) + (s / 3600.0)
                return None

            if lat_raw:
                d_lat = dms_to_decimal(lat_raw)
                if d_lat is not None:
                    if lat_ref == "S":
                        d_lat = -d_lat
                    lat = round(d_lat, 6)

            if lon_raw:
                d_lon = dms_to_decimal(lon_raw)
                if d_lon is not None:
                    if lon_ref == "W":
                        d_lon = -d_lon
                    lon = round(d_lon, 6)
    except Exception:
        pass

    return lat, lon, captured_at


def process_single_image(
    file_bytes: bytes,
    original_filename: str,
    inspection_id: int,
    user_id: Optional[int],
    source: str,
    db: Session,
) -> UploadResultItem:
    """
    Validate, check duplicates, analyze quality, rotate upright, and store a single image file.
    Returns UploadResultItem (accepted, warning, or rejected with explicit reason).
    """
    # 1. File size check (config: MAX_UPLOAD_SIZE_MB)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        return UploadResultItem(
            filename=original_filename,
            status="rejected",
            message=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    # 2. Genuine image validation via Pillow (cannot be fooled by renamed text file)
    try:
        pil_img = Image.open(io.BytesIO(file_bytes))
        pil_img.load()  # Force reading entire image buffer
    except Exception:
        return UploadResultItem(
            filename=original_filename,
            status="rejected",
            message="Invalid or corrupted image format. File is not a valid image.",
        )

    # Format check: Only JPG/JPEG and PNG allowed
    image_format = (pil_img.format or "").upper()
    if image_format not in ["JPEG", "JPG", "PNG"]:
        return UploadResultItem(
            filename=original_filename,
            status="rejected",
            message=f"Unsupported format '{image_format}'. Only JPG, JPEG, and PNG are allowed.",
        )

    # 3. Minimum resolution check (min 640 x 480 in either orientation)
    width, height = pil_img.size
    if (width < settings.MIN_IMAGE_WIDTH and height < settings.MIN_IMAGE_WIDTH) or (
        width < settings.MIN_IMAGE_HEIGHT or height < settings.MIN_IMAGE_HEIGHT
    ):
        return UploadResultItem(
            filename=original_filename,
            status="rejected",
            message=f"Image resolution {width}x{height} is too low. Minimum required is 640x480.",
        )

    # 4. Duplicate check via SHA-256 in the same inspection
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    duplicate_exists = (
        db.query(ImageModel)
        .filter(
            ImageModel.inspection_id == inspection_id,
            ImageModel.file_hash == file_hash,
        )
        .first()
    )
    if duplicate_exists:
        return UploadResultItem(
            filename=original_filename,
            status="rejected",
            message="duplicate",
        )

    # 5. Extract EXIF GPS and capture time before stripping/transforming
    gps_lat, gps_lon, captured_at = parse_gps_and_time(pil_img)

    # 6. Fix rotation using EXIF orientation tag
    try:
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass

    final_width, final_height = pil_img.size

    # 7. Quality check via OpenCV (Laplacian variance & grayscale mean)
    blur_score, brightness_score, quality_status, quality_notes = assess_image_quality(
        pil_img
    )

    # 8. Save image to disk using a random UUID filename (never user filename)
    ext = ALLOWED_IMAGE_FORMATS.get(image_format, "jpg")
    uuid_filename = f"{uuid.uuid4().hex}.{ext}"

    # Directory: backend/storage/uploads/<inspection_id>/
    target_dir = settings.upload_path / str(inspection_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_filepath = target_dir / uuid_filename

    # Save to disk
    if ext in ["jpg", "jpeg"]:
        # Convert RGBA to RGB for JPEG compatibility
        if pil_img.mode in ("RGBA", "P"):
            pil_img = pil_img.convert("RGB")
        pil_img.save(target_filepath, format="JPEG", quality=92)
    else:
        pil_img.save(target_filepath, format="PNG")

    saved_size_bytes = target_filepath.stat().st_size
    relative_path = f"{settings.UPLOAD_DIR}/{inspection_id}/{uuid_filename}".replace(
        "\\", "/"
    )

    # 9. Save image record to database
    db_image = ImageModel(
        inspection_id=inspection_id,
        uploaded_by=user_id,
        file_path=relative_path,
        original_filename=original_filename,
        file_hash=file_hash,
        width_px=final_width,
        height_px=final_height,
        file_size_bytes=saved_size_bytes,
        source=source,
        blur_score=blur_score,
        brightness_score=brightness_score,
        quality_status=quality_status,
        quality_notes=quality_notes,
        gps_latitude=gps_lat,
        gps_longitude=gps_lon,
        captured_at=captured_at,
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    # Status for upload response: "warning" if quality warning, else "accepted"
    result_status = "warning" if quality_status == "warning" else "accepted"
    result_message = quality_notes if quality_status == "warning" else "Image accepted successfully"

    return UploadResultItem(
        filename=original_filename,
        status=result_status,
        message=result_message,
        image=ImageResponse.model_validate(db_image),
    )
