"""AI Analysis Service for InfraScan.

Runs trained deep learning models on uploaded inspection images:
1. Multi-class road distress detection (YOLOv8s RDD2022) with configurable detector list.
2. Semantic crack segmentation (SMP UnetPlusPlus ResNet-34) with exact training preprocessing:
   - RGB channel order
   - Reflection padding to multiple of 32
   - ImageNet normalization
   - Optimal thresholding and small component removal (< 20 px)
   - PNG mask saving in MASK_DIR
3. Quantitative sub-pixel crack geometry characterization via measure_crack (width_mode="edt2").

Note: The analysis runner performs detection and segmentation, not classification.
The segmentation model uses a ResNet-34 encoder (U-Net++ ResNet34); no separate image classifier is used.
"""

from datetime import datetime, timezone
from pathlib import Path
import logging
import time
import math
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.models.analysis import AnalysisRun, CrackMeasurement, Detection, ImageScale, ModelVersion, run_models
from app.models.image import Image as ImageModel
from app.ai.geometry import measure_crack
from app.services.model_registry import record_inference_metrics
from app.services.event_service import publish

logger = logging.getLogger(__name__)

# In-memory lazy model caches (loaded once per worker process)
_YOLO_MODELS: Dict[str, Any] = {}
_RTDETR_MODELS: Dict[str, Any] = {}
_SEG_MODEL: Optional[Any] = None
_SEG_MODEL_PATH: Optional[str] = None


def resolve_disk_path(path_str: str) -> Path:
    """Resolve relative or absolute path against project root and BASE_DIR."""
    p = Path(path_str)
    if p.is_absolute() and p.exists():
        return p
    # Try resolving relative to BASE_DIR (infrascan/backend)
    candidate = (BASE_DIR / p).resolve()
    if candidate.exists():
        return candidate
    # Try resolving relative to project root (infrascan)
    candidate_root = (BASE_DIR.parent / p).resolve()
    if candidate_root.exists():
        return candidate_root
    # Try resolving relative to ML_MODELS_DIR
    candidate_ml = (settings.ml_models_path / p).resolve()
    if candidate_ml.exists():
        return candidate_ml
    # Also handle ml/models/detection vs ml/detection fallback
    p_str = str(p).replace("\\", "/")
    if "ml/models/detection/" in p_str:
        alt_str = p_str.replace("ml/models/detection/", "ml/detection/")
        alt = (BASE_DIR.parent / alt_str).resolve()
        if alt.exists():
            return alt
    elif "ml/detection/" in p_str:
        alt_str = p_str.replace("ml/detection/", "ml/models/detection/")
        alt = (BASE_DIR.parent / alt_str).resolve()
        if alt.exists():
            return alt
    return candidate


def get_yolo_model(weights_path: str):
    """Lazily load and cache YOLO model from weights path."""
    resolved = resolve_disk_path(weights_path)
    if not resolved.exists():
        raise FileNotFoundError(
            f"YOLO weights file not found at '{resolved}'. "
            f"Please verify YOLO_WEIGHTS in configuration or download baseline weights."
        )
    key = str(resolved)
    if key not in _YOLO_MODELS:
        from ultralytics import YOLO
        _YOLO_MODELS[key] = YOLO(str(resolved))
    return _YOLO_MODELS[key]


def get_rtdetr_model(weights_path: str):
    """Lazily load and cache RT-DETR model from weights path using Ultralytics RTDETR."""
    resolved = resolve_disk_path(weights_path)
    if not resolved.exists():
        raise FileNotFoundError(
            f"RT-DETR weights file not found at '{resolved}'. "
            f"Please verify CODEBRIM_WEIGHTS in configuration or download baseline weights."
        )
    key = str(resolved)
    if key not in _RTDETR_MODELS:
        from ultralytics import RTDETR
        _RTDETR_MODELS[key] = RTDETR(str(resolved))
    return _RTDETR_MODELS[key]


def get_segmentation_model(weights_path: str):
    """Lazily load and cache SMP UnetPlusPlus ResNet-34 model from weights path."""
    global _SEG_MODEL, _SEG_MODEL_PATH
    resolved = resolve_disk_path(weights_path)
    if not resolved.exists():
        raise FileNotFoundError(
            f"Segmentation weights file not found at '{resolved}'. "
            f"Please verify SEG_WEIGHTS in configuration or download baseline weights."
        )
    key = str(resolved)
    if _SEG_MODEL is None or _SEG_MODEL_PATH != key:
        import segmentation_models_pytorch as smp
        import torch

        model = smp.UnetPlusPlus(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=3,
            classes=1,
        )
        checkpoint = torch.load(str(resolved), map_location="cpu")
        state_dict = checkpoint["model_state_dict"] if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint else checkpoint
        # Strip potential 'module.' prefixes from DataParallel training
        clean_sd = {k.replace("module.", ""): v for k, v in state_dict.items()}
        model.load_state_dict(clean_sd)
        model.eval()

        _SEG_MODEL = model
        _SEG_MODEL_PATH = key
    return _SEG_MODEL


def warmup_models() -> None:
    """Execute 1 dummy forward pass on registered models to eliminate cold-start latency spike."""
    import torch
    dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)

    # 1. Warmup YOLO detector
    try:
        yolo = get_yolo_model(settings.YOLO_WEIGHTS)
        with torch.inference_mode():
            _ = yolo.predict(source=dummy_img, imgsz=640, verbose=False)
        logger.info("YOLO detector warmed up successfully.")
    except Exception as e:
        logger.debug(f"YOLO warmup skipped or failed: {e}")

    # 2. Warmup RT-DETR detector
    try:
        rtdetr = get_rtdetr_model(settings.CODEBRIM_WEIGHTS)
        with torch.inference_mode():
            _ = rtdetr.predict(source=dummy_img, imgsz=640, verbose=False)
        logger.info("RT-DETR detector warmed up successfully.")
    except Exception as e:
        logger.debug(f"RT-DETR warmup skipped or failed: {e}")

    # 3. Warmup U-Net++ segmentation model
    try:
        seg = get_segmentation_model(settings.SEG_WEIGHTS)
        dummy_tensor = torch.zeros((1, 3, 256, 256), dtype=torch.float32)
        with torch.inference_mode():
            _ = seg(dummy_tensor)
        logger.info("U-Net++ segmentation model warmed up successfully.")
    except Exception as e:
        logger.debug(f"U-Net++ warmup skipped or failed: {e}")


def execute_image_analysis(
    run_id: int,
    image_id: int,
    db: Session,
    mm_per_pixel: Optional[float] = None,
    override_detectors: Optional[List[str]] = None,
) -> AnalysisRun:
    """
    Execute AI analysis pipeline synchronously for a created AnalysisRun record.
    Never modifies the original image.
    Catches errors and marks status='failed' without crashing the caller.
    """
    run = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
    if not run:
        raise ValueError(f"AnalysisRun #{run_id} not found in database.")

    image = db.query(ImageModel).filter(ImageModel.image_id == image_id).first()
    if not image:
        run.status = "failed"
        run.error_message = f"Associated image #{image_id} not found."
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return run

    # Guard: never run analysis on rejected images
    if image.quality_status == "rejected":
        run.status = "failed"
        run.error_message = f"Image #{image_id} has quality_status='rejected' and cannot be analyzed."
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return run

    run.status = "in_progress"
    run.started_at = datetime.now(timezone.utc)
    publish(
        db=db,
        event_type="analysis.stage_started",
        entity_type="analysis",
        entity_id=run.run_id,
        audience={"all": True},
        payload={
            "run_id": run.run_id,
            "image_id": image_id,
            "stage": "detection_and_segmentation",
        },
    )
    db.commit()

    # Look up active scale for image if mm_per_pixel not explicitly passed
    scale = (
        db.query(ImageScale)
        .filter(ImageScale.image_id == image_id, ImageScale.is_current == True)
        .first()
    )
    if mm_per_pixel is None and scale is not None:
        mm_per_pixel = scale.mm_per_pixel

    start_time = time.time()
    try:
        warnings_list: List[str] = []

        # 1. Resolve and read original image (read-only, never modified)
        img_path = resolve_disk_path(image.file_path)
        if not img_path.exists():
            raise FileNotFoundError(f"Original image file not found on disk: {img_path}")

        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            raise ValueError(f"Failed to decode image from disk: {img_path}")

        orig_h, orig_w = img_bgr.shape[:2]

        # 2. Check maximum dimension and resize for inference if necessary
        max_dim = max(orig_h, orig_w)
        if max_dim > settings.MAX_SIDE:
            scale_ratio = settings.MAX_SIDE / float(max_dim)
            infer_w = int(round(orig_w * scale_ratio))
            infer_h = int(round(orig_h * scale_ratio))
            img_bgr_infer = cv2.resize(img_bgr, (infer_w, infer_h), interpolation=cv2.INTER_AREA)
            is_scaled = True
            scale_x = orig_w / float(infer_w)
            scale_y = orig_h / float(infer_h)
            image_scale_note = (
                f"Image resized from {orig_w}x{orig_h} to {infer_w}x{infer_h} "
                f"(max side exceeded {settings.MAX_SIDE}px) for model inference and mapped back to original resolution."
            )
        else:
            img_bgr_infer = img_bgr
            is_scaled = False
            scale_x = 1.0
            scale_y = 1.0
            image_scale_note = "Inference performed at original image resolution."

        img_rgb_infer = cv2.cvtColor(img_bgr_infer, cv2.COLOR_BGR2RGB)
        used_model_ids: List[str] = []

        # 3. Object Detection Pipeline (Multi-detector routing)
        asset = image.inspection.asset if (image.inspection and image.inspection.asset) else None
        asset_type = (asset.asset_type or "").lower().strip() if asset else None
        material_type = (asset.material_type or "").lower().strip() if asset else None

        detection_configs = settings.get_detection_models()

        if override_detectors:
            chosen_detectors = [
                d for d in detection_configs
                if d.get("name") in override_detectors or d.get("model_id") in override_detectors
            ]
        elif getattr(settings, "RUN_ALL_DETECTORS", False):
            chosen_detectors = list(detection_configs)
        else:
            chosen_detectors = []
            if asset_type:
                chosen_detectors = [
                    d for d in detection_configs
                    if asset_type in [a.lower() for a in d.get("applicable_asset_types", [])]
                ]
            if not chosen_detectors and material_type:
                chosen_detectors = [
                    d for d in detection_configs
                    if material_type in [m.lower() for m in d.get("applicable_material_types", [])]
                ]
            if not chosen_detectors:
                chosen_detectors = list(detection_configs)
                warnings_list.append(
                    f"No detector specifically matched asset type '{asset_type or 'unknown'}'; ran all detectors as fallback."
                )

        detections_to_insert: List[Detection] = []

        for det_cfg in chosen_detectors:
            model_id = det_cfg.get("model_id") or det_cfg.get("name", "yolov8s_rdd2022")
            weights_path = det_cfg.get("weights_path", settings.YOLO_WEIGHTS)
            class_names = det_cfg.get("class_names", {})
            conf_thresh = det_cfg.get("conf") or det_cfg.get("confidence", settings.YOLO_CONF)
            det_imgsz = det_cfg.get("imgsz", 640)
            model_class = str(det_cfg.get("model_class", "yolo")).lower()

            try:
                if model_class == "rtdetr":
                    detector_model = get_rtdetr_model(weights_path)
                else:
                    detector_model = get_yolo_model(weights_path)
            except (FileNotFoundError, OSError) as load_err:
                logger.warning(f"Detector '{model_id}' skipped: {load_err}")
                warnings_list.append(f"Detector '{model_id}' skipped: {load_err}")
                continue

            used_model_ids.append(model_id)

            t_det = time.time()
            results = detector_model.predict(
                source=img_rgb_infer,
                imgsz=det_imgsz,
                conf=conf_thresh,
                verbose=False,
            )
            det_lat_ms = (time.time() - t_det) * 1000.0
            try:
                record_inference_metrics(db, model_id, det_lat_ms, success=True)
            except Exception:
                pass

            names_map = getattr(detector_model, "names", {})

            for res in results:
                if res.boxes is not None:
                    for box in res.boxes:
                        coords = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        cls_idx = int(box.cls[0].cpu().numpy())

                        # Map coordinates back to original image pixels
                        x_min = float(coords[0] * scale_x)
                        y_min = float(coords[1] * scale_y)
                        x_max = float(coords[2] * scale_x)
                        y_max = float(coords[3] * scale_y)

                        # Clamp within original bounds
                        x_min = max(0.0, min(float(orig_w), x_min))
                        y_min = max(0.0, min(float(orig_h), y_min))
                        x_max = max(0.0, min(float(orig_w), x_max))
                        y_max = max(0.0, min(float(orig_h), y_max))

                        dmg_type = None
                        if isinstance(names_map, dict):
                            dmg_type = names_map.get(cls_idx) or names_map.get(str(cls_idx))
                        if dmg_type is None:
                            dmg_type = class_names.get(cls_idx) or class_names.get(str(cls_idx)) or f"D{cls_idx}"

                        dmg_label = class_names.get(cls_idx) or class_names.get(str(cls_idx)) or str(dmg_type)

                        det_row = Detection(
                            run_id=run.run_id,
                            model_id=model_id,
                            damage_type=str(dmg_type),
                            damage_label=str(dmg_label),
                            confidence=conf,
                            x_min=round(x_min, 2),
                            y_min=round(y_min, 2),
                            x_max=round(x_max, 2),
                            y_max=round(y_max, 2),
                        )
                        detections_to_insert.append(det_row)

        # 4. Semantic Crack Segmentation Pipeline (U-Net++ ResNet-34)
        # Preprocessing matches evaluate_seg_test.py (lines 41-98) & 09_train_seg_kaggle.ipynb:
        # - RGB color format (no CLAHE)
        # - Reflection padding to multiple of 32
        # - ImageNet mean/std normalization
        # - Sigmoid activation & probability map unpadding
        import torch

        seg_model_id = "unetplusplus_crack500"
        used_model_ids.append(seg_model_id)
        seg_model = get_segmentation_model(settings.SEG_WEIGHTS)

        cur_h, cur_w = img_rgb_infer.shape[:2]
        pad_h = (32 - (cur_h % 32)) % 32
        pad_w = (32 - (cur_w % 32)) % 32

        if pad_h > 0 or pad_w > 0:
            img_padded = cv2.copyMakeBorder(
                img_rgb_infer.astype(np.float32), 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT_101
            )
        else:
            img_padded = img_rgb_infer.astype(np.float32)

        # ImageNet normalization: mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        norm_img = (img_padded / 255.0 - mean) / std

        tensor = torch.from_numpy(norm_img.transpose(2, 0, 1)).unsqueeze(0).float()
        t_seg = time.time()
        with torch.inference_mode():
            logits = seg_model(tensor)
            prob_map = torch.sigmoid(logits).squeeze().cpu().numpy()
        seg_lat_ms = (time.time() - t_seg) * 1000.0
        try:
            record_inference_metrics(db, seg_model_id, seg_lat_ms, success=True)
        except Exception:
            pass

        # Remove padding
        prob_map = prob_map[:cur_h, :cur_w]

        # Map back to original image dimensions if scaled
        if is_scaled:
            prob_map = cv2.resize(prob_map, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

        # Threshold segmentation probability map
        seg_threshold = settings.get_segmentation_threshold()
        mask_bin = (prob_map > seg_threshold).astype(np.uint8)

        # Remove high-frequency noise components smaller than 20 pixels
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_bin, connectivity=8)
        cleaned_mask = np.zeros_like(mask_bin)
        for lbl in range(1, num_labels):
            if stats[lbl, cv2.CC_STAT_AREA] >= 20:
                cleaned_mask[labels == lbl] = 1

        # Save binary mask as PNG (0 or 255) at the original image size in MASK_DIR
        mask_dir = settings.mask_path
        mask_dir.mkdir(parents=True, exist_ok=True)
        mask_filename = f"run_{run.run_id}_mask.png"
        mask_disk_path = mask_dir / mask_filename
        mask_png = (cleaned_mask * 255).astype(np.uint8)
        cv2.imwrite(str(mask_disk_path), mask_png)

        rel_mask_path = f"{settings.MASK_DIR}/{mask_filename}".replace("\\", "/")

        # 5. Quantitative Crack Geometry Measurement
        # Invokes copied module backend/app/ai/geometry.py with width_mode='edt2'
        geom_stats, _ = measure_crack(
            cleaned_mask,
            mm_per_pixel=mm_per_pixel,
            min_area_px=20,
            width_mode="edt2",
        )

        crack_pixels = int(cleaned_mask.sum())
        total_pixels = orig_h * orig_w
        density_pct = round((crack_pixels / float(total_pixels)) * 100.0, 4) if total_pixels > 0 else 0.0

        length_mm = round(float(geom_stats["length_mm"]), 2) if geom_stats.get("length_mm") is not None else None
        avg_width_mm = round(float(geom_stats["avg_width_mm"]), 2) if geom_stats.get("avg_width_mm") is not None else None
        max_width_mm = round(float(geom_stats["max_width_mm"]), 2) if geom_stats.get("max_width_mm") is not None else None

        scale_id = scale.scale_id if scale else None
        length_mm_unc = None
        width_mm_unc = None
        meas_note = None

        if scale and mm_per_pixel is not None:
            u_ratio = (scale.uncertainty_percent or 0.0) / 100.0
            method_err = mm_per_pixel * 1.0
            if avg_width_mm is not None:
                width_mm_unc = round(math.sqrt((method_err) ** 2 + (avg_width_mm * u_ratio) ** 2), 2)
            if length_mm is not None:
                length_mm_unc = round((length_mm * u_ratio) + method_err, 2)
            if not scale.camera_perpendicular:
                meas_note = "perspective not corrected: approximate"

        measurement = CrackMeasurement(
            run_id=run.run_id,
            mask_path=rel_mask_path,
            threshold=seg_threshold,
            crack_pixels=crack_pixels,
            length_px=round(float(geom_stats.get("length_px", 0.0)), 2),
            avg_width_px=round(float(geom_stats.get("avg_width_px", 0.0)), 2),
            max_width_px=round(float(geom_stats.get("max_width_px", 0.0)), 2),
            p95_width_px=round(float(geom_stats.get("p95_width_px", 0.0)), 2),
            area_px=int(geom_stats.get("area_px", crack_pixels)),
            density_percent=density_pct,
            orientation_deg=round(float(geom_stats.get("orientation_deg", 0.0)), 2),
            num_components=int(geom_stats.get("num_components", 0)),
            num_branch_points=int(geom_stats.get("num_branch_points", 0)),
            num_end_points=int(geom_stats.get("num_end_points", 0)),
            mm_per_pixel=mm_per_pixel,
            length_mm=length_mm,
            avg_width_mm=avg_width_mm,
            max_width_mm=max_width_mm,
            width_mode="edt2",
            scale_id=scale_id,
            length_mm_uncertainty=length_mm_unc,
            width_mm_uncertainty=width_mm_unc,
            measurement_note=meas_note,
        )

        # 6. Save results and link models
        for det in detections_to_insert:
            db.add(det)
        db.add(measurement)

        # Register run models in junction table
        for m_id in set(used_model_ids):
            # Verify if ModelVersion exists in db, if so link
            mv = db.query(ModelVersion).filter(ModelVersion.model_id == m_id).first()
            if mv:
                db.execute(
                    run_models.insert().values(run_id=run.run_id, model_id=m_id)
                )

        elapsed = round(time.time() - start_time, 3)
        run.status = "done"
        run.seconds = elapsed
        seg_domain_note = "Segmentation model (U-Net++ ResNet-34) trained on road pavement crops (CRACK500)."
        if image_scale_note:
            run.image_scale_note = f"{image_scale_note} {seg_domain_note}"
        else:
            run.image_scale_note = seg_domain_note
        if warnings_list:
            run.error_message = "; ".join(warnings_list)
        run.finished_at = datetime.now(timezone.utc)
        publish(
            db=db,
            event_type="analysis.completed",
            entity_type="analysis",
            entity_id=run.run_id,
            audience={"all": True},
            payload={
                "run_id": run.run_id,
                "image_id": image_id,
                "seconds": elapsed,
                "detections_count": len(detections_to_insert),
                "crack_pixels": crack_pixels,
            },
        )
        db.commit()
        db.refresh(run)

        # Hook: damage severity assessment (advisory, failures must never fail analysis)
        try:
            from app.services.severity_service import assess_and_save_run
            assess_and_save_run(run_id=run.run_id, db=db)
        except Exception as sev_err:
            logger.error(f"Severity assessment failed for run {run.run_id}: {sev_err}")

        return run

    except Exception as exc:
        db.rollback()
        elapsed = round(time.time() - start_time, 3)
        run = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
        if run:
            run.status = "failed"
            run.error_message = str(exc)
            run.seconds = elapsed
            run.finished_at = datetime.now(timezone.utc)
            publish(
                db=db,
                event_type="analysis.failed",
                entity_type="analysis",
                entity_id=run.run_id,
                audience={"all": True},
                payload={
                    "run_id": run.run_id,
                    "image_id": image_id,
                    "error": str(exc),
                },
            )
            db.commit()
            db.refresh(run)
        return run


def create_and_enqueue_analysis(
    image_id: int,
    db: Session,
    mm_per_pixel: Optional[float] = None,
) -> AnalysisRun:
    """Create a pending AnalysisRun record and return it."""
    run = AnalysisRun(
        image_id=image_id,
        status="pending",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    publish(
        db=db,
        event_type="analysis.queued",
        entity_type="analysis",
        entity_id=run.run_id,
        audience={"all": True},
        payload={"run_id": run.run_id, "image_id": image_id},
    )
    db.commit()
    db.refresh(run)
    return run

