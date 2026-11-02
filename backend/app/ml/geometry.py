"""Crack geometry measured from a binary segmentation mask.

Every length and width in this module is in pixels. These numbers are not
millimetres unless a camera calibration or a known scale is supplied, and
this project does not have that scale.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

PHYSICAL_SCALE_NOTE = (
    "Measurements are in pixels, not millimetres. "
    "No camera calibration or known physical scale is available."
)


def to_binary_mask(mask: np.ndarray, threshold: int = 127) -> np.ndarray:
    """Return a uint8 mask with values 0 or 255."""
    if mask.ndim == 3:
        gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    else:
        gray = mask
    binary = np.where(gray > threshold, 255, 0).astype(np.uint8)
    return binary


def skeletonize(binary: np.ndarray) -> np.ndarray:
    """Morphological skeleton. Input and output are uint8 0/255."""
    image = (binary > 0).astype(np.uint8) * 255
    skeleton = np.zeros(image.shape, np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while True:
        eroded = cv2.erode(image, element)
        opened = cv2.dilate(eroded, element)
        subset = cv2.subtract(image, opened)
        skeleton = cv2.bitwise_or(skeleton, subset)
        image = eroded
        if cv2.countNonZero(image) == 0:
            break
    return skeleton


def extract_geometry(mask: np.ndarray) -> dict[str, Any]:
    """Estimate area, length, width, bounding size, and coverage from a mask."""
    binary = to_binary_mask(mask)
    height, width = binary.shape[:2]
    total = int(height * width)
    area = int(cv2.countNonZero(binary))
    empty = {
        "crack_pixel_area": 0,
        "crack_length_px": 0.0,
        "crack_width_px_mean": 0.0,
        "crack_width_px_median": 0.0,
        "bbox_xmin": None,
        "bbox_ymin": None,
        "bbox_xmax": None,
        "bbox_ymax": None,
        "bbox_width_px": 0,
        "bbox_height_px": 0,
        "coverage_percent": 0.0,
        "image_width": width,
        "image_height": height,
        "unit": "pixels",
        "physical_scale_note": PHYSICAL_SCALE_NOTE,
    }
    if area == 0 or total == 0:
        return empty

    ys, xs = np.where(binary > 0)
    xmin, xmax = int(xs.min()), int(xs.max())
    ymin, ymax = int(ys.min()), int(ys.max())
    skeleton = skeletonize(binary)
    length = int(cv2.countNonZero(skeleton))
    distance = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
    if length > 0:
        widths = distance[skeleton > 0] * 2.0
        mean_width = float(np.mean(widths))
        median_width = float(np.median(widths))
    else:
        mean_width = float(area)
        median_width = mean_width
        length = 1

    return {
        "crack_pixel_area": area,
        "crack_length_px": float(length),
        "crack_width_px_mean": round(mean_width, 3),
        "crack_width_px_median": round(median_width, 3),
        "bbox_xmin": xmin,
        "bbox_ymin": ymin,
        "bbox_xmax": xmax,
        "bbox_ymax": ymax,
        "bbox_width_px": int(xmax - xmin + 1),
        "bbox_height_px": int(ymax - ymin + 1),
        "coverage_percent": round(100.0 * area / total, 4),
        "image_width": width,
        "image_height": height,
        "unit": "pixels",
        "physical_scale_note": PHYSICAL_SCALE_NOTE,
    }
