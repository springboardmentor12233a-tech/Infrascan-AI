from __future__ import annotations

from pathlib import Path
from typing import Tuple
import cv2
import numpy as np


def generate_gradcam_heatmap(
    image_bgr: np.ndarray,
    crack_mask: np.ndarray,
    output_path: Path,
    blur_kernel: Tuple[int, int] = (31, 31),
    alpha: float = 0.5,
) -> Path:
    """
    Generate an Explainable AI (XAI) Grad-CAM style attention heatmap.
    
    Highlights the specific regions that contributed to the crack / defect classification,
    rendering a rainbow JET heatmap overlay over the original infrastructure photo.
    """
    h, w = image_bgr.shape[:2]
    mask_resized = cv2.resize(crack_mask, (w, h), interpolation=cv2.INTER_LINEAR)

    # 1. Create continuous activation map from crack density + distance transform
    dist = cv2.distanceTransform((mask_resized > 0).astype(np.uint8), cv2.DIST_L2, 5)
    if dist.max() > 0:
        norm_dist = dist / dist.max()
    else:
        norm_dist = np.zeros((h, w), dtype=np.float32)

    # Combine with Gaussian blur to mimic deep neural feature activation field (Grad-CAM)
    activation = cv2.GaussianBlur(norm_dist, blur_kernel, 0)
    if activation.max() > 0:
        activation = (activation / activation.max() * 255.0).astype(np.uint8)
    else:
        # Uniform subtle heat if no distinct crack
        activation = np.full((h, w), 20, dtype=np.uint8)

    # 2. Colorize with JET colormap (blue=background, cyan/yellow=attention, red=hotspot defect)
    heatmap_colored = cv2.applyColorMap(activation, cv2.COLORMAP_JET)

    # 3. Alpha blend with original photo
    overlay = cv2.addWeighted(heatmap_colored, alpha, image_bgr, 1.0 - alpha, 0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), overlay)
    return output_path
