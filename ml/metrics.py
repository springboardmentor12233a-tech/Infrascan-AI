from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class SegmentationMetrics:
    intersection_over_union: float
    dice: float
    precision: float
    recall: float


def segmentation_metrics(prediction: np.ndarray, target: np.ndarray, threshold: float = 0.5) -> SegmentationMetrics:
    predicted = np.asarray(prediction) >= threshold
    expected = np.asarray(target).astype(bool)
    true_positive = int(np.logical_and(predicted, expected).sum())
    false_positive = int(np.logical_and(predicted, ~expected).sum())
    false_negative = int(np.logical_and(~predicted, expected).sum())
    union = true_positive + false_positive + false_negative
    return SegmentationMetrics(
        intersection_over_union=true_positive / union if union else 1.0,
        dice=(2 * true_positive) / (2 * true_positive + false_positive + false_negative)
        if true_positive + false_positive + false_negative else 1.0,
        precision=true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0,
        recall=true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0,
    )


def extract_geometry(mask: np.ndarray, pixel_size_mm: float | None = None) -> dict[str, float | int | None]:
    binary = np.asarray(mask).astype(bool)
    ys, xs = np.where(binary)
    if not len(xs):
        return {"area_pixels": 0, "length_pixels": 0, "width_pixels": 0, "area_mm2": None}
    length = max(int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
    width = max(1, int(binary.sum() / length))
    area_mm2 = float(binary.sum() * pixel_size_mm**2) if pixel_size_mm else None
    return {
        "area_pixels": int(binary.sum()),
        "length_pixels": length,
        "width_pixels": width,
        "area_mm2": area_mm2,
    }
