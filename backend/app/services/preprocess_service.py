"""
Service module for executing image preprocessing and persistence.
Saves enhanced images to storage/processed/<inspection_id>/<uuid>.jpg
and records pipeline execution metadata in the database.
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Optional
import uuid
import cv2
from sqlalchemy.orm import Session

from app.ai.preprocessing import PreprocessConfig, preprocess, save_enhanced
from app.config import BASE_DIR, settings
from app.database import SessionLocal
from app.models.image import Image as ImageModel

logger = logging.getLogger(__name__)


def resolve_disk_path(file_path_str: str) -> Path:
    """Resolve database relative path to absolute filesystem path."""
    p = Path(file_path_str)
    if not p.is_absolute():
        return BASE_DIR / p
    return p


def process_image_preprocessing(
    db: Session,
    image_id: int,
    config: Optional[PreprocessConfig] = None,
) -> Optional[ImageModel]:
    """
    Execute preprocessing pipeline for a saved image.
    Never overwrites or modifies the original file.
    Updates preprocess_status, processed_file_path, and preprocess_steps.
    """
    image = db.query(ImageModel).filter(ImageModel.image_id == image_id).first()
    if not image:
        logger.warning(f"Image {image_id} not found in database for preprocessing.")
        return None

    try:
        orig_disk_path = resolve_disk_path(image.file_path)
        if not orig_disk_path.exists():
            image.preprocess_status = "failed"
            image.preprocess_steps = "Original file not found on disk"
            db.commit()
            logger.error(f"Image file not found on disk: {orig_disk_path}")
            return image

        # Read original image in BGR format
        img_bgr = cv2.imread(str(orig_disk_path))
        if img_bgr is None:
            image.preprocess_status = "failed"
            image.preprocess_steps = "Failed to decode original image with OpenCV"
            db.commit()
            logger.error(f"Failed to decode image with OpenCV: {orig_disk_path}")
            return image

        # Build pipeline configuration
        if config is None:
            cfg = PreprocessConfig(
                model_input_size=settings.MODEL_INPUT_SIZE,
                normalize_mode=settings.NORMALIZE_MODE,
                enable_contrast=settings.ENABLE_CONTRAST,
                enable_denoise=settings.ENABLE_DENOISE,
                enable_sharpen=settings.ENABLE_SHARPEN,
                clahe_clip_limit=settings.CLAHE_CLIP_LIMIT,
                clahe_tile_grid=settings.CLAHE_TILE_GRID,
            )
        else:
            cfg = config

        # Run pipeline
        result = preprocess(img_bgr, config=cfg)

        # Remove previous processed file if re-running
        if image.processed_file_path:
            old_path = resolve_disk_path(image.processed_file_path)
            if old_path.exists():
                try:
                    old_path.unlink()
                except Exception:
                    pass

        # Target storage location: backend/storage/processed/<inspection_id>/<uuid>.jpg
        target_dir = settings.processed_path / str(image.inspection_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        uuid_filename = f"{uuid.uuid4().hex}.jpg"
        target_filepath = target_dir / uuid_filename

        # Save enhanced image as high-quality JPEG (quality 95)
        save_success = save_enhanced(target_filepath, result.enhanced_image)
        if not save_success or not target_filepath.exists():
            image.preprocess_status = "failed"
            image.preprocess_steps = "Failed to write enhanced image to disk"
            db.commit()
            return image

        rel_path = f"{settings.PROCESSED_DIR}/{image.inspection_id}/{uuid_filename}".replace(
            "\\", "/"
        )

        # Update database image record
        image.processed_file_path = rel_path
        image.preprocess_status = "done"
        image.preprocess_steps = ", ".join(result.steps_applied)
        image.preprocessed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(image)
        logger.info(f"Image {image_id} preprocessed successfully. Steps: {image.preprocess_steps}")
        return image

    except Exception as exc:
        db.rollback()
        logger.exception(f"Preprocessing error for image {image_id}: {exc}")
        try:
            image.preprocess_status = "failed"
            image.preprocess_steps = f"Error: {str(exc)[:200]}"
            db.commit()
        except Exception:
            pass
        return image


def run_preprocess_background(image_id: int) -> None:
    """Thread-safe background task handler with its own isolated database session."""
    db = SessionLocal()
    try:
        process_image_preprocessing(db, image_id)
    except Exception as exc:
        logger.exception(f"Background task preprocessing exception for image {image_id}: {exc}")
    finally:
        db.close()
