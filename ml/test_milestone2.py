from pathlib import Path

import numpy as np

from ml.metrics import extract_geometry, segmentation_metrics
from ml.quality import assess_image


def test_segmentation_metrics_and_geometry():
    target = np.array([[1, 1, 0], [0, 0, 0], [0, 0, 0]])
    prediction = np.array([[1, 0, 0], [0, 0, 0], [0, 0, 0]])
    metrics = segmentation_metrics(prediction, target)
    assert metrics.intersection_over_union == 0.5
    assert metrics.dice == 2 / 3
    assert extract_geometry(target)["area_pixels"] == 2


def test_quality_assessment_uses_real_image():
    path = next(Path("datasets/Positive").glob("*.jpg"))
    quality = assess_image(path)
    assert quality.width > 0
    assert quality.height > 0
    assert quality.format == "JPEG"
