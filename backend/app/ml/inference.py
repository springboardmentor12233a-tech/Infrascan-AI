"""Run the available baselines on one BGR image.

Each task reports its own status:
- completed: a saved weight file ran and produced this result
- unavailable: the weight file is not on disk, so no prediction was invented
- failed: the weight file exists but inference raised an error

Pixel geometry is computed only from a segmentation mask produced in this call.
"""

from __future__ import annotations

import json
from typing import Any

import cv2
import numpy as np

from app.ml.geometry import extract_geometry
from app.ml.paths import CLASSIFIER_WEIGHTS, REPORTS_DIR, UNET_WEIGHTS, YOLO_WEIGHTS
from app.ml.preprocess import preprocess_for_model, resize_stretch, to_bgr
from app.ml.quality import quality_report_from_array

CLASSIFIER_SIZE = 64
UNET_SIZE = 128
PATCH_GRID_SIDE = 256
# Boxes are shown only when the saved validation mAP50 clears this bar.
# The current Czech fine-tune is far below it, so its boxes are withheld.
RELIABLE_MAP50 = 0.05
UNRELIABLE_DETECTION = (
    "Detection model requires further training and validation. "
    "No reliable bounding boxes generated."
)

_classifier = None
_unet = None
_yolo = None
_classifier_meta: dict[str, Any] = {}
_unet_meta: dict[str, Any] = {}


def model_status() -> dict[str, Any]:
    return {
        "classifier": {
            "name": "SmallCNN",
            "task": "binary crack vs non-crack patch classification",
            "weights": str(CLASSIFIER_WEIGHTS),
            "available": CLASSIFIER_WEIGHTS.is_file(),
            "framework": "PyTorch",
        },
        "segmentation": {
            "name": "UNet",
            "task": "binary crack segmentation",
            "weights": str(UNET_WEIGHTS),
            "available": UNET_WEIGHTS.is_file(),
            "framework": "PyTorch",
        },
        "detection": {
            "name": "YOLOv8n",
            "task": "RDD2022 Czech bounding-box detection (D00, D10, D20, D40)",
            "weights": str(YOLO_WEIGHTS),
            "available": YOLO_WEIGHTS.is_file(),
            "framework": "Ultralytics YOLOv8n fine-tune" if YOLO_WEIGHTS.is_file() else "not trained",
            "note": (
                "This file is a model trained by scripts/ml/train_yolo.py on the local Czech subset. "
                "It is not an off-the-shelf COCO detector."
            ),
        },
    }


def _torch():
    import torch

    return torch


def _load_classifier():
    global _classifier, _classifier_meta
    if _classifier is not None or not CLASSIFIER_WEIGHTS.is_file():
        return _classifier
    torch = _torch()
    from app.ml.nets import SmallCNN

    checkpoint = torch.load(CLASSIFIER_WEIGHTS, map_location="cpu", weights_only=False)
    model = SmallCNN(num_classes=2)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    _classifier = model
    _classifier_meta = {key: checkpoint.get(key) for key in ("model_name", "dataset", "input_size", "metrics", "config")}
    return model


def _load_unet():
    global _unet, _unet_meta
    if _unet is not None or not UNET_WEIGHTS.is_file():
        return _unet
    torch = _torch()
    from app.ml.nets import UNet

    checkpoint = torch.load(UNET_WEIGHTS, map_location="cpu", weights_only=False)
    base = int(checkpoint.get("config", {}).get("base_channels", 8))
    model = UNet(base=base)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    _unet = model
    _unet_meta = {key: checkpoint.get(key) for key in ("model_name", "dataset", "input_size", "metrics", "config")}
    return model


def _load_yolo():
    global _yolo
    if _yolo is not None or not YOLO_WEIGHTS.is_file():
        return _yolo
    from ultralytics import YOLO

    _yolo = YOLO(str(YOLO_WEIGHTS))
    return _yolo


def _classify(image_bgr: np.ndarray) -> dict[str, Any]:
    if not CLASSIFIER_WEIGHTS.is_file():
        return {
            "status": "unavailable",
            "label": None,
            "confidence": None,
            "model": "SmallCNN",
            "detail": "Classifier weights were not found. Run scripts/ml/train_classifier.py.",
        }
    try:
        torch = _torch()
        model = _load_classifier()
        working = resize_stretch(image_bgr, (PATCH_GRID_SIDE, PATCH_GRID_SIDE))
        crack_probs: list[float] = []
        with torch.no_grad():
            for top in range(0, PATCH_GRID_SIDE, CLASSIFIER_SIZE):
                for left in range(0, PATCH_GRID_SIDE, CLASSIFIER_SIZE):
                    patch = working[top : top + CLASSIFIER_SIZE, left : left + CLASSIFIER_SIZE]
                    tensor = preprocess_for_model(
                        patch,
                        size=(CLASSIFIER_SIZE, CLASSIFIER_SIZE),
                        imagenet=True,
                        keep_aspect=False,
                        reduce_noise=False,
                    )
                    batch = torch.from_numpy(tensor).unsqueeze(0)
                    probabilities = torch.softmax(model(batch), dim=1)[0]
                    crack_probs.append(float(probabilities[1]))
        crack_fraction = float(np.mean(np.array(crack_probs) >= 0.5))
        max_prob = float(max(crack_probs)) if crack_probs else 0.0
        mean_prob = float(np.mean(crack_probs)) if crack_probs else 0.0
        label = "crack" if max_prob >= 0.5 and crack_fraction > 0 else "non_crack"
        confidence = max_prob if label == "crack" else 1.0 - mean_prob
        return {
            "status": "completed",
            "label": label,
            "confidence": round(confidence, 4),
            "crack_patch_fraction": round(crack_fraction, 4),
            "max_crack_probability": round(max_prob, 4),
            "mean_crack_probability": round(mean_prob, 4),
            "model": "SmallCNN",
            "detail": (
                "The network was trained on 64x64 DeepCrack patches. "
                "This image was split into a 4x4 grid of 64x64 patches. "
                "The label is crack when at least one patch is predicted as crack."
            ),
            "training_metrics": _classifier_meta.get("metrics"),
        }
    except Exception as exc:
        return {"status": "failed", "label": None, "confidence": None, "model": "SmallCNN", "detail": str(exc)}


def _segment(image_bgr: np.ndarray) -> tuple[dict[str, Any], np.ndarray | None]:
    height, width = image_bgr.shape[:2]
    if not UNET_WEIGHTS.is_file():
        return (
            {
                "status": "unavailable",
                "model": "UNet",
                "detail": "U-Net weights were not found. Run scripts/ml/train_unet.py.",
            },
            None,
        )
    try:
        torch = _torch()
        model = _load_unet()
        tensor = preprocess_for_model(
            image_bgr,
            size=(UNET_SIZE, UNET_SIZE),
            imagenet=True,
            keep_aspect=False,
            reduce_noise=False,
        )
        batch = torch.from_numpy(tensor).unsqueeze(0)
        with torch.no_grad():
            logits = model(batch)
            probability = torch.sigmoid(logits)[0, 0].cpu().numpy()
        small = (probability >= 0.5).astype(np.uint8) * 255
        mask = cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)
        return (
            {
                "status": "completed",
                "model": "UNet",
                "input_size": UNET_SIZE,
                "threshold": 0.5,
                "detail": (
                    "Mask was predicted at 128x128 and resized with nearest-neighbour "
                    "back to the original image size. Training used the same resize for "
                    "images and masks."
                ),
                "training_metrics": _unet_meta.get("metrics"),
            },
            mask,
        )
    except Exception as exc:
        return (
            {"status": "failed", "model": "UNet", "detail": str(exc)},
            None,
        )


def _validation_map50() -> float | None:
    report = REPORTS_DIR / "yolo_metrics.json"
    if not report.is_file():
        return None
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
        value = payload.get("validation_metrics", {}).get("map50")
        if value is None:
            return None
        return float(value)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _detect(image_bgr: np.ndarray) -> dict[str, Any]:
    if not YOLO_WEIGHTS.is_file():
        return {
            "status": "unavailable",
            "model": "YOLOv8n",
            "reliable": False,
            "validation_map50": _validation_map50(),
            "detections": [],
            "candidate_count": 0,
            "detail": "YOLO weights were not found. Run scripts/ml/prepare_yolo.py and scripts/ml/train_yolo.py.",
        }
    try:
        model = _load_yolo()
        results = model.predict(image_bgr, conf=0.25, verbose=False)
        candidates: list[dict[str, Any]] = []
        names = results[0].names if results else {}
        boxes = results[0].boxes if results else None
        if boxes is not None:
            for box in boxes:
                class_id = int(box.cls.item())
                x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
                candidates.append(
                    {
                        "class_id": class_id,
                        "class_name": str(names.get(class_id, class_id)),
                        "confidence": round(float(box.conf.item()), 4),
                        "xmin": round(x1, 2),
                        "ymin": round(y1, 2),
                        "xmax": round(x2, 2),
                        "ymax": round(y2, 2),
                    }
                )
        map50 = _validation_map50()
        reliable = map50 is not None and map50 >= RELIABLE_MAP50
        if reliable:
            detail = (
                "Boxes come from the fine-tuned YOLOv8n checkpoint. "
                f"Validation mAP50 is {map50}, which clears {RELIABLE_MAP50}."
            )
            shown = candidates
        else:
            detail = UNRELIABLE_DETECTION
            if map50 is None:
                detail += " No validation mAP50 report was found, so boxes are withheld."
            else:
                detail += f" Validation mAP50 on the labeled Czech subset was {map50}."
            if candidates:
                detail += (
                    f" The checkpoint emitted {len(candidates)} candidate boxes above 0.25. "
                    "They are not shown."
                )
            shown = []
        return {
            "status": "completed",
            "model": "YOLOv8n",
            "reliable": reliable,
            "validation_map50": map50,
            "detections": shown,
            "candidate_count": len(candidates),
            "confidence_threshold": 0.25,
            "detail": detail,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "model": "YOLOv8n",
            "reliable": False,
            "detections": [],
            "candidate_count": 0,
            "detail": str(exc),
        }


def draw_overlay(image_bgr: np.ndarray, mask: np.ndarray | None, detections: list[dict[str, Any]]) -> np.ndarray:
    overlay = image_bgr.copy()
    if mask is not None:
        color = np.zeros_like(overlay)
        color[:, :, 2] = mask
        overlay = cv2.addWeighted(overlay, 1.0, color, 0.45, 0)
    palette = {
        "D00": (0, 200, 0),
        "D10": (255, 180, 0),
        "D20": (0, 140, 255),
        "D40": (0, 0, 255),
    }
    for det in detections:
        color = palette.get(det.get("class_name", ""), (255, 255, 0))
        p1 = (int(det["xmin"]), int(det["ymin"]))
        p2 = (int(det["xmax"]), int(det["ymax"]))
        cv2.rectangle(overlay, p1, p2, color, 2)
        label = f"{det.get('class_name', '')} {det.get('confidence', 0):.2f}"
        cv2.putText(overlay, label, (p1[0], max(16, p1[1] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    return overlay


def analyze_image(image_bgr: np.ndarray) -> dict[str, Any]:
    """Quality, classification, detection, segmentation, geometry, and an overlay."""
    image_bgr = to_bgr(image_bgr)
    quality = quality_report_from_array(image_bgr)
    classification = _classify(image_bgr)
    detection = _detect(image_bgr)
    segmentation, mask = _segment(image_bgr)
    geometry = extract_geometry(mask) if mask is not None else None
    if geometry is None:
        geometry_block = {
            "status": "unavailable",
            "detail": "Geometry is calculated from a segmentation mask. No mask was produced.",
            "measurements": None,
        }
    else:
        geometry_block = {"status": "completed", "detail": geometry["physical_scale_note"], "measurements": geometry}
    overlay = draw_overlay(image_bgr, mask, detection.get("detections") or [])
    return {
        "quality": quality,
        "classification": classification,
        "detection": detection,
        "segmentation": segmentation,
        "geometry": geometry_block,
        "mask": mask,
        "overlay_bgr": overlay,
    }
