from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np


def extract_crack_geometry(
    binary_mask: np.ndarray,
    scale_mm_per_px: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Extract geometric and morphological properties from a binary crack mask.
    
    Parameters:
        binary_mask: 2D binary numpy array where crack pixels are > 0 (or True).
        scale_mm_per_px: Optional physical scale factor (mm per pixel).
        
    Returns:
        Dict containing length_px, avg_width_px, max_width_px, area_px,
        density_pct, orientation_degrees, and physical measurements if calibrated.
    """
    mask = (np.asarray(binary_mask) > 0).astype(np.uint8)
    h, w = mask.shape[:2]
    total_surface_pixels = h * w
    crack_pixel_count = int(np.sum(mask))

    if crack_pixel_count == 0:
        return {
            "crack_detected": False,
            "area_px": 0,
            "length_px": 0.0,
            "avg_width_px": 0.0,
            "max_width_px": 0.0,
            "crack_density_pct": 0.0,
            "orientation_degrees": 0.0,
            "area_mm2": None,
            "length_mm": None,
            "max_width_mm": None,
            "avg_width_mm": None,
            "scale_calibrated": False,
        }

    # 1. Crack Area and Density
    crack_density_pct = float((crack_pixel_count / total_surface_pixels) * 100.0)

    # 2. Skeletonization (medial axis thinning) to estimate crack centerline length
    skeleton = np.zeros_like(mask)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    temp_mask = mask.copy()

    while True:
        eroded = cv2.erode(temp_mask, element)
        opened = cv2.dilate(eroded, element)
        temp = cv2.subtract(temp_mask, opened)
        skeleton = cv2.bitwise_or(skeleton, temp)
        temp_mask = eroded.copy()
        if cv2.countNonZero(temp_mask) == 0:
            break

    skeleton_pixels = int(np.sum(skeleton > 0))
    # Account for diagonal pixel distances (~1.2x heuristic)
    length_px = float(skeleton_pixels * 1.15) if skeleton_pixels > 0 else float(crack_pixel_count)

    # 3. Euclidean Distance Transform to determine crack width profile
    dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    # The distance transform returns radius from edge; diameter = 2 * distance
    crack_distances = dist_transform[mask > 0]
    
    if len(crack_distances) > 0:
        max_width_px = float(np.max(crack_distances) * 2.0)
        avg_width_px = float(np.mean(crack_distances) * 2.0)
    else:
        max_width_px = 1.0
        avg_width_px = 1.0

    # Ensure length >= width
    if length_px < max_width_px:
        length_px = max_width_px * 1.5

    # 4. Orientation Angle via Principal Moments
    moments = cv2.moments(mask)
    orientation_deg = 0.0
    if moments["mu20"] != moments["mu02"]:
        theta = 0.5 * math.atan2(2 * moments["mu11"], moments["mu20"] - moments["mu02"])
        orientation_deg = float(math.degrees(theta))
        if orientation_deg < 0:
            orientation_deg += 180.0

    # 5. Physical Scale Conversion if calibrated
    area_mm2 = None
    length_mm = None
    max_width_mm = None
    avg_width_mm = None

    if scale_mm_per_px and scale_mm_per_px > 0:
        area_mm2 = round(float(crack_pixel_count * (scale_mm_per_px ** 2)), 2)
        length_mm = round(float(length_px * scale_mm_per_px), 2)
        max_width_mm = round(float(max_width_px * scale_mm_per_px), 2)
        avg_width_mm = round(float(avg_width_px * scale_mm_per_px), 2)

    return {
        "crack_detected": True,
        "area_px": crack_pixel_count,
        "length_px": round(length_px, 1),
        "avg_width_px": round(avg_width_px, 2),
        "max_width_px": round(max_width_px, 2),
        "crack_density_pct": round(crack_density_pct, 3),
        "orientation_degrees": round(orientation_deg, 1),
        "area_mm2": area_mm2,
        "length_mm": length_mm,
        "max_width_mm": max_width_mm,
        "avg_width_mm": avg_width_mm,
        "scale_calibrated": bool(scale_mm_per_px and scale_mm_per_px > 0),
    }
