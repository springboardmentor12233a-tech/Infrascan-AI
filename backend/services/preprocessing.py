"""
Image Upload Validation and Preprocessing Service.

Implements file validation (MIME types, file size limits), corrupt file checks,
and preprocessing pipelines that mirror the training protocols.
"""

from pathlib import Path
from typing import Tuple
import uuid
import re
import cv2
from fastapi import HTTPException, UploadFile
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = PROJECT_ROOT / "static" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Constraints
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp"
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


def save_uploaded_image(raw_bytes: bytes, original_filename: str) -> Tuple[Path, str]:
    """Saves raw upload bytes to static/uploads and returns disk path & relative URL path."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    clean_name = re.sub(r"[^\w\.-]", "_", original_filename or "upload.jpg")
    prefix = uuid.uuid4().hex[:8]
    stored_name = f"{prefix}_{clean_name}"
    disk_path = UPLOADS_DIR / stored_name
    with open(disk_path, "wb") as f:
        f.write(raw_bytes)
    rel_path = f"static/uploads/{stored_name}"
    return disk_path, rel_path


async def validate_and_decode_upload(file: UploadFile) -> Tuple[np.ndarray, bytes]:
    """
    Validates uploaded image MIME type, file size, and decodability.

    Args:
        file: FastAPI UploadFile object.

    Returns:
        Tuple of (decoded_bgr_image: np.ndarray, raw_bytes: bytes)

    Raises:
        HTTPException (400) if validation fails.
    """
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Allowed types: JPEG, PNG, WEBP, BMP."
        )

    raw_bytes = await file.read()
    if len(raw_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowable limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    # Decode using OpenCV
    np_arr = np.frombuffer(raw_bytes, np.uint8)
    image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image_bgr is None or image_bgr.size == 0:
        raise HTTPException(
            status_code=400,
            detail="Corrupted or invalid image data. Unable to decode image."
        )

    return image_bgr, raw_bytes


def preprocess_classification(image_bgr: np.ndarray) -> np.ndarray:
    """
    Preprocesses decoded image for MobileNetV2 classification.
    Converts BGR to RGB, resizes to (224, 224), scales to [0.0, 1.0],
    and expands dimensions to (1, 224, 224, 3).
    """
    img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (224, 224), interpolation=cv2.INTER_LINEAR)
    img_normalized = img_resized.astype(np.float32) / 255.0
    return np.expand_dims(img_normalized, axis=0)


def preprocess_segmentation(image_bgr: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    Preprocesses decoded image for U-Net crack segmentation.
    Converts BGR to RGB, captures original (H, W), resizes to (256, 256),
    scales to [0.0, 1.0], and expands dimensions to (1, 256, 256, 3).

    Returns:
        (preprocessed_tensor, (orig_height, orig_width))
    """
    orig_h, orig_w = image_bgr.shape[:2]
    img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (256, 256), interpolation=cv2.INTER_LINEAR)
    img_normalized = img_resized.astype(np.float32) / 255.0
    tensor = np.expand_dims(img_normalized, axis=0)
    return tensor, (orig_h, orig_w)

