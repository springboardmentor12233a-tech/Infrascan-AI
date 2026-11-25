"""Classifier Service for InfraScan.

Performs crop classification for crack screening using ResNet-50 trained on SDNET2018.
Enforces:
1. Crop dimension guard (<= 600px).
2. Exact training preprocessing: CLAHE + ImageNet normalization to 224x224.
3. Mandatory screening disclaimer on all outputs:
   "Initial screening classification; defect detection model provides localized assessment. AI result for engineer review, not a final structural safety verdict."
"""

from pathlib import Path
import time
from typing import Any, Dict, Optional, Tuple, Union
import cv2
import numpy as np
import torch
import torch.nn as nn
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.models.analysis import ModelVersion
from app.services.model_registry import record_inference_metrics

_CLASSIFIER_MODEL: Optional[Any] = None
_CLASSIFIER_PATH: Optional[str] = None

SCREENING_DISCLAIMER = (
    "Initial screening classification; defect detection model provides localized assessment. "
    "AI result for engineer review, not a final structural safety verdict."
)


def load_classifier(weights_path: str = "../ml/models/classification/sdnet2018/best.pth"):
    """Lazily load and cache ResNet-50 classifier model."""
    global _CLASSIFIER_MODEL, _CLASSIFIER_PATH

    resolved = BASE_DIR / weights_path if not Path(weights_path).is_absolute() else Path(weights_path)
    if not resolved.exists():
        resolved_alt = settings.ml_models_path / weights_path
        if resolved_alt.exists():
            resolved = resolved_alt

    key = str(resolved)
    if _CLASSIFIER_MODEL is None or _CLASSIFIER_PATH != key:
        import torchvision.models as models
        model = models.resnet50(weights=None)
        model.fc = nn.Linear(model.fc.in_features, 1)

        if resolved.exists():
            checkpoint = torch.load(str(resolved), map_location="cpu")
            state_dict = (
                checkpoint["model_state_dict"]
                if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint
                else checkpoint
            )
            clean_sd = {k.replace("module.", ""): v for k, v in state_dict.items()}
            model.load_state_dict(clean_sd)
        model.eval()
        _CLASSIFIER_MODEL = model
        _CLASSIFIER_PATH = key

    return _CLASSIFIER_MODEL


def classify_crop(
    crop_bgr: np.ndarray,
    db: Optional[Session] = None,
    threshold: float = 0.50,
    model_id: str = "resnet50_sdnet2018",
) -> Dict[str, Any]:
    """
    Classify an image crop for crack presence.
    Rejects crops with width or height > 600px.
    """
    h, w = crop_bgr.shape[:2]
    if max(h, w) > 600:
        raise ValueError(
            f"Crop dimension {w}x{h} exceeds maximum 600px limit. "
            "Please provide a tighter bounding crop around the candidate region."
        )

    start_time = time.time()
    success = False
    try:
        # Preprocessing:
        # 1. CLAHE in LAB space
        lab = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_clahe = clahe.apply(l)
        lab_clahe = cv2.merge((l_clahe, a, b))
        bgr_clahe = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
        rgb = cv2.cvtColor(bgr_clahe, cv2.COLOR_BGR2RGB)

        # 2. Resize to 224x224
        resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_AREA)

        # 3. ImageNet normalization: (x/255 - mean) / std
        float_img = resized.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        norm = (float_img - mean) / std

        # 4. Transpose to (1, 3, 224, 224)
        tensor = torch.from_numpy(norm.transpose(2, 0, 1)).unsqueeze(0)

        # 5. Inference
        model = load_classifier()
        with torch.inference_mode():
            logits = model(tensor)
            prob = torch.sigmoid(logits).item()

        crack_prob = round(float(prob), 4)
        is_cracked = bool(crack_prob >= threshold)
        label = "cracked" if is_cracked else "uncracked"
        latency_ms = round((time.time() - start_time) * 1000.0, 2)
        success = True

        if db is not None:
            record_inference_metrics(db, model_id, latency_ms, success=True)

        return {
            "crack_probability": crack_prob,
            "is_cracked": is_cracked,
            "label": label,
            "threshold": threshold,
            "model_id": model_id,
            "crop_dimensions": {"width": w, "height": h},
            "latency_ms": latency_ms,
            "screening_disclaimer": SCREENING_DISCLAIMER,
        }
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000.0, 2)
        if db is not None:
            record_inference_metrics(db, model_id, latency_ms, success=False)
        raise e
