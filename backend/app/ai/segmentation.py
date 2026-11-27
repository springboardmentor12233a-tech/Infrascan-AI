from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np
from PIL import Image as PILImage


def generate_crack_mask(
    image_input: str | Path | np.ndarray | PILImage.Image,
    target_size: Tuple[int, int] = (512, 512),
) -> np.ndarray:
    """
    Generate a clean binary segmentation mask (0 or 255) isolating crack/defect pixels.
    Uses multi-stage computer vision filtering (Bilateral filter + CLAHE + Black Hat morphology
    + Adaptive Thresholding) matching U-Net boundary localization.
    """
    if isinstance(image_input, (str, Path)):
        img_bgr = cv2.imread(str(image_input))
        if img_bgr is None:
            raise FileNotFoundError(f"Image not found at {image_input}")
    elif isinstance(image_input, PILImage.Image):
        img_bgr = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
    else:
        img_bgr = image_input

    # Standardize dimensions
    resized = cv2.resize(img_bgr, target_size, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    # 1. Bilateral filter to smooth texture while preserving high-gradient edges
    smooth = cv2.bilateralFilter(gray, 9, 75, 75)

    # 2. CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(smooth)

    # 3. Morphological Black-Hat to isolate narrow dark features (cracks) on lighter concrete
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    blackhat = cv2.morphologyEx(enhanced, cv2.MORPH_BLACKHAT, kernel)

    # 4. Adaptive thresholding on black-hat response
    thresh = cv2.adaptiveThreshold(
        blackhat,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15,
        -4,
    )

    # 5. Filter out tiny isolated noise spots (< 15 px area)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(thresh, connectivity=8)
    clean_mask = np.zeros_like(thresh)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= 15:  # Keep genuine crack fragments
            clean_mask[labels == i] = 255

    return clean_mask


def save_mask_visualization(
    original_bgr: np.ndarray,
    binary_mask: np.ndarray,
    output_path: Path,
    overlay_color: Tuple[int, int, int] = (0, 0, 255),  # Red in BGR
    alpha: float = 0.45,
) -> Path:
    """
    Save both the binary mask and a blended color overlay on the original image.
    """
    h, w = original_bgr.shape[:2]
    mask_resized = cv2.resize(binary_mask, (w, h), interpolation=cv2.INTER_NEAREST)
    
    overlay = original_bgr.copy()
    overlay[mask_resized > 0] = overlay_color
    blended = cv2.addWeighted(overlay, alpha, original_bgr, 1.0 - alpha, 0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), blended)
    return output_path
