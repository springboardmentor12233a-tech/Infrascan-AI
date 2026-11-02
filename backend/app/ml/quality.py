"""Image quality checks used before crack analysis.

Scores are heuristics for field photos. They are not a camera-calibration
or structural assessment.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from app.ml.preprocess import read_upload, to_gray

MIN_SIDE = 64
BLUR_THRESHOLD = 100.0
BRIGHTNESS_LOW = 40.0
BRIGHTNESS_HIGH = 230.0
CONTRAST_LOW = 12.0


def _scores(gray: np.ndarray) -> tuple[float, float, float]:
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    return blur, brightness, contrast


def quality_report_from_array(
    image: np.ndarray,
    min_side: int = MIN_SIDE,
    blur_threshold: float = BLUR_THRESHOLD,
    brightness_low: float = BRIGHTNESS_LOW,
    brightness_high: float = BRIGHTNESS_HIGH,
    contrast_low: float = CONTRAST_LOW,
) -> dict[str, Any]:
    if image is None or image.size == 0:
        return _invalid("Empty image")
    if image.ndim not in (2, 3):
        return _invalid(f"Unsupported image shape {getattr(image, 'shape', None)}")

    height, width = int(image.shape[0]), int(image.shape[1])
    gray = to_gray(image)
    blur, brightness, contrast = _scores(gray)
    flags: list[str] = []

    if width < min_side or height < min_side:
        flags.append("too_small")
    if blur < blur_threshold:
        flags.append("blurry")
    if brightness < brightness_low:
        flags.append("low_light")
    elif brightness > brightness_high:
        flags.append("overexposed")
    if contrast < contrast_low:
        flags.append("low_contrast")

    if "too_small" in flags:
        status = "too_small"
    elif "blurry" in flags:
        status = "blurry"
    elif "low_light" in flags:
        status = "low_light"
    elif "overexposed" in flags:
        status = "overexposed"
    elif "low_contrast" in flags:
        status = "low_contrast"
    else:
        status = "ok"

    return {
        "valid": True,
        "width": width,
        "height": height,
        "channels": 1 if image.ndim == 2 else int(image.shape[2]),
        "blur_score": round(blur, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "status": status,
        "flags": flags,
        "thresholds": {
            "min_side": min_side,
            "blur": blur_threshold,
            "brightness_low": brightness_low,
            "brightness_high": brightness_high,
            "contrast_low": contrast_low,
        },
        "notes": [
            "Blur is the variance of the Laplacian. Lower means blurrier.",
            "Brightness is the mean gray level from 0 to 255.",
            "Contrast is the standard deviation of the gray image.",
        ],
    }


def quality_report_from_bytes(image_bytes: bytes) -> dict[str, Any]:
    try:
        image = read_upload(image_bytes)
    except ValueError as exc:
        return _invalid(str(exc))
    return quality_report_from_array(image)


def _invalid(reason: str) -> dict[str, Any]:
    return {
        "valid": False,
        "width": 0,
        "height": 0,
        "channels": 0,
        "blur_score": None,
        "brightness": None,
        "contrast": None,
        "status": "invalid",
        "flags": ["invalid"],
        "thresholds": {},
        "notes": [reason],
    }
