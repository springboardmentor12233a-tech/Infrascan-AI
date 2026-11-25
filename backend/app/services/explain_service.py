"""Explainable AI (XAI) service orchestrator for InfraScan.

Coordinates:
- Model caching and lookup (shared with analysis_service)
- Input image preparation and resolution
- Calling pure explain functions (app.ai.explain)
- File persistence (heatmap NPY/PNG and overlay PNG in EXPLAIN_DIR)
- Database record creation and lifecycle management in the explanations table
"""

import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.database import SessionLocal
from app.models.analysis import AnalysisRun, run_models
from app.models.explanation import Explanation
from app.models.image import Image as ImageModel
from app.services.analysis_service import (
    get_rtdetr_model,
    get_segmentation_model,
    get_yolo_model,
    resolve_disk_path,
)
from app.ai.explain import (
    compare_maps,
    explain_detector,
    explain_segmentation,
    ExplanationOutput,
)

logger = logging.getLogger(__name__)

# Method-model compatibility mapping
SUPPORTED_METHODS_BY_TASK = {
    "segmentation": ["gradcam", "gradcampp", "saliency"],
    "detection": ["eigencam"],
}


def validate_model_method_pairs(
    model_ids: List[str],
    methods: List[str],
    detection_model_ids: List[str],
    seg_model_ids: List[str],
) -> None:
    """
    Validate that requested methods are supported for the requested models.
    Raises ValueError with a clear message if unsupported.
    """
    for m_id in model_ids:
        is_seg = m_id in seg_model_ids or "unet" in m_id.lower() or "seg" in m_id.lower()
        is_det = m_id in detection_model_ids or "yolo" in m_id.lower() or "rtdetr" in m_id.lower() or "det" in m_id.lower()

        for meth in methods:
            norm_m = meth.lower().replace("-", "").replace("_", "")
            if is_seg:
                allowed = ["gradcam", "gradcampp", "gradcamplusplus", "saliency"]
                if norm_m not in allowed:
                    raise ValueError(
                        f"Explanation method '{meth}' is not supported for segmentation model '{m_id}'. "
                        f"Supported methods for segmentation are: ['gradcam', 'gradcampp', 'saliency']."
                    )
            elif is_det:
                allowed = ["eigencam"]
                if norm_m not in allowed:
                    raise ValueError(
                        f"Explanation method '{meth}' is not supported for object detector '{m_id}'. "
                        f"Supported methods for detectors are: ['eigencam']."
                    )
            else:
                # Unknown model type
                raise ValueError(
                    f"Model '{m_id}' is not recognized as a supported segmentation or detection model."
                )


def execute_single_explanation(
    db: Session,
    explanation_id: int,
    image_id: int,
    run_id: int,
    model_id: str,
    method: str,
) -> Explanation:
    """
    Execute a single explanation task, write output files to EXPLAIN_DIR, and update DB.
    Never raises an uncaught exception; sets status='failed' on error.
    """
    record = db.query(Explanation).filter(Explanation.explanation_id == explanation_id).first()
    if not record:
        logger.error(f"Explanation #{explanation_id} not found in database.")
        return None

    try:
        # 1. Resolve image
        image = db.query(ImageModel).filter(ImageModel.image_id == image_id).first()
        if not image:
            raise FileNotFoundError(f"Associated image #{image_id} not found.")

        img_path = resolve_disk_path(image.file_path)
        if not img_path.exists():
            raise FileNotFoundError(f"Original image file not found on disk: {img_path}")

        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            raise ValueError(f"Failed to decode image from disk: {img_path}")

        # 2. Identify task and load model
        det_configs = settings.get_detection_models()
        det_cfg = next((d for d in det_configs if (d.get("name") == model_id or d.get("model_id") == model_id)), None)

        is_det = det_cfg is not None or "yolo" in model_id.lower() or "rtdetr" in model_id.lower()
        is_seg = model_id == "unetplusplus_crack500" or "seg" in model_id.lower() or "unet" in model_id.lower()

        if not is_det and not is_seg:
            raise ValueError(f"Unrecognized model_id '{model_id}' for explanation.")

        explain_dir = settings.explain_path
        explain_dir.mkdir(parents=True, exist_ok=True)

        t0 = time.time()

        if is_seg:
            target_type = "mask"
            model = get_segmentation_model(settings.SEG_WEIGHTS)
            thresh = settings.get_segmentation_threshold()
            output: ExplanationOutput = explain_segmentation(
                model=model,
                img_bgr=img_bgr,
                method=method,
                threshold=thresh,
                max_side=settings.MAX_SIDE,
                model_name=model_id,
            )
        else:
            target_type = "detections"
            model_class = det_cfg.get("model_class", "yolo") if det_cfg else ("rtdetr" if "rtdetr" in model_id.lower() else "yolo")
            weights = det_cfg.get("weights_path") if det_cfg else (settings.CODEBRIM_WEIGHTS if model_class == "rtdetr" else settings.YOLO_WEIGHTS)
            imgsz = det_cfg.get("imgsz", 640) if det_cfg else 640

            if model_class == "rtdetr":
                detector = get_rtdetr_model(weights)
            else:
                detector = get_yolo_model(weights)

            output: ExplanationOutput = explain_detector(
                detector_model=detector,
                img_bgr=img_bgr,
                model_class=model_class,
                method=method,
                imgsz=imgsz,
                max_side=settings.MAX_SIDE,
                model_name=model_id,
            )

        elapsed = round(time.time() - t0, 3)

        # 3. Save files to EXPLAIN_DIR
        base_filename = f"img_{image_id}_run_{run_id}_{model_id}_{method}_{explanation_id}"
        heatmap_filename = f"{base_filename}_heatmap.npy"
        overlay_filename = f"{base_filename}_overlay.png"

        heatmap_disk_path = explain_dir / heatmap_filename
        overlay_disk_path = explain_dir / overlay_filename

        # Save heatmap as numpy float32
        np.save(str(heatmap_disk_path), output.heatmap)

        # Save overlay PNG
        with open(overlay_disk_path, "wb") as f:
            f.write(output.overlay_png)

        rel_heatmap_path = f"{settings.EXPLAIN_DIR}/{heatmap_filename}".replace("\\", "/")
        rel_overlay_path = f"{settings.EXPLAIN_DIR}/{overlay_filename}".replace("\\", "/")

        # 4. Update database record
        record.status = "done"
        record.target = target_type
        record.heatmap_path = rel_heatmap_path
        record.overlay_path = rel_overlay_path
        record.params_json = json.dumps(output.metadata)
        record.warnings_json = json.dumps(output.metadata.get("warnings", []))
        record.seconds = elapsed
        record.error_message = None
        db.commit()
        db.refresh(record)
        return record

    except Exception as e:
        logger.error(f"Error computing explanation #{explanation_id}: {e}", exc_info=True)
        record.status = "failed"
        record.error_message = str(e)
        record.seconds = round(time.time() - t0, 3) if "t0" in locals() else 0.0
        db.commit()
        db.refresh(record)
        return record


def run_explanations_in_background(
    explanation_ids: List[int],
    image_id: int,
    run_id: int,
) -> None:
    """Background worker processing a batch of requested explanation jobs."""
    db: Session = SessionLocal()
    try:
        for eid in explanation_ids:
            exp = db.query(Explanation).filter(Explanation.explanation_id == eid).first()
            if not exp:
                continue
            execute_single_explanation(
                db=db,
                explanation_id=eid,
                image_id=image_id,
                run_id=run_id,
                model_id=exp.model_id,
                method=exp.method,
            )
    except Exception as e:
        logger.error(f"Background explanation batch execution error: {e}", exc_info=True)
    finally:
        db.close()


def cleanup_image_explanations(image_id: int, db: Session) -> int:
    """
    Remove all physical explanation files from disk for an image before its DB deletion.
    Returns the count of files removed.
    """
    explanations = db.query(Explanation).filter(Explanation.image_id == image_id).all()
    removed_count = 0
    for exp in explanations:
        if exp.heatmap_path:
            p = resolve_disk_path(exp.heatmap_path)
            if p.exists():
                try:
                    p.unlink()
                    removed_count += 1
                except Exception:
                    pass
        if exp.overlay_path:
            p = resolve_disk_path(exp.overlay_path)
            if p.exists():
                try:
                    p.unlink()
                    removed_count += 1
                except Exception:
                    pass
        db.delete(exp)
    db.flush()
    return removed_count
