from typing import Tuple, Union
import cv2
import numpy as np
from PIL import Image

from app.config import settings


def _to_grayscale_numpy(image_input: Union[Image.Image, np.ndarray]) -> np.ndarray:
    """Helper to convert PIL Image or color NumPy array to single-channel grayscale."""
    if isinstance(image_input, Image.Image):
        np_img = np.array(image_input.convert("RGB"))
    else:
        np_img = image_input

    if len(np_img.shape) == 3:
        # Check if 3-channel; convert to grayscale (handles RGB/BGR adequately)
        return cv2.cvtColor(np_img, cv2.COLOR_BGR2GRAY)
    return np_img


def calculate_blur_score(image_input: Union[Image.Image, np.ndarray]) -> float:
    """
    Calculate image sharpness / blur score via the variance of the Laplacian.
    Higher values indicate sharper edges, lower values indicate blur.
    """
    gray = _to_grayscale_numpy(image_input)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def calculate_brightness_score(image_input: Union[Image.Image, np.ndarray]) -> float:
    """
    Calculate average image brightness via mean grayscale pixel intensity (0 to 255).
    """
    gray = _to_grayscale_numpy(image_input)
    return float(np.mean(gray))


def assess_image_quality(
    image_input: Union[Image.Image, np.ndarray]
) -> Tuple[float, float, str, str]:
    """
    Evaluate image blurriness and brightness against configured thresholds.
    Returns (blur_score, brightness_score, quality_status, quality_notes).
    """
    blur_score = calculate_blur_score(image_input)
    brightness_score = calculate_brightness_score(image_input)

    # Evaluate against thresholds defined in config
    notes = []
    if blur_score < settings.BLUR_THRESHOLD:
        notes.append(
            f"Image may be blurry (score: {blur_score:.1f} < {settings.BLUR_THRESHOLD:.1f})"
        )

    if brightness_score < settings.BRIGHTNESS_MIN:
        notes.append(
            f"Image is too dark / underexposed (score: {brightness_score:.1f} < {settings.BRIGHTNESS_MIN:.1f})"
        )
    elif brightness_score > settings.BRIGHTNESS_MAX:
        notes.append(
            f"Image is overexposed / too bright (score: {brightness_score:.1f} > {settings.BRIGHTNESS_MAX:.1f})"
        )

    if notes:
        quality_status = "warning"
        quality_notes = "; ".join(notes)
    else:
        quality_status = "passed"
        quality_notes = "Quality check passed"

    return blur_score, brightness_score, quality_status, quality_notes
