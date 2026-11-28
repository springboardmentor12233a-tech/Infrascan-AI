"""Real OpenCV-based Image Quality Assessment and preprocessing."""

from pathlib import Path
import cv2
import numpy as np


def assess_image_quality(image_path: str) -> dict:
    """
    Validate and assess image quality using OpenCV:
    - Resolution check
    - Blur assessment via Laplacian variance
    - Brightness (mean luminance) and contrast (std luminance)
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Invalid or unreadable image file: {image_path}")

    height, width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    issues = []
    if width < 320 or height < 240:
        issues.append("Low Resolution")
    if blur_score < 50.0:
        issues.append("Blurry")
    if brightness < 40.0 or brightness > 220.0:
        issues.append("Poor Lighting")
    if contrast < 20.0:
        issues.append("Low Contrast")

    status = "Good Quality" if not issues else issues[0]
    return {
        "width": width,
        "height": height,
        "blur_variance": round(blur_score, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "quality_status": status,
        "issues": issues,
    }

