"""Pytest test suite for crack geometry measurement module."""

import numpy as np
import pytest

import sys
from pathlib import Path

# Add infrascan root to sys.path so 'ml.geometry' can be imported anywhere
infrascan_root = Path(__file__).resolve().parents[3]
if str(infrascan_root) not in sys.path:
    sys.path.insert(0, str(infrascan_root))

try:
    from ml.geometry.crack_geometry import measure_crack
except ImportError:
    from infrascan.ml.geometry.crack_geometry import measure_crack


def test_known_line_length_within_3_percent():
    """Verify that a straight line of known length (100 px) is measured within 3% error."""
    mask = np.zeros((80, 180), dtype=np.uint8)
    # Horizontal line of length 100 pixels, width 3 pixels
    mask[38:41, 40:140] = 1

    results, skel = measure_crack(mask, min_area_px=20)
    measured_len = results["length_px"]
    true_len = 100.0

    relative_error = abs(measured_len - true_len) / true_len
    assert relative_error <= 0.03, f"Length {measured_len:.2f} px deviates by {relative_error*100:.2f}% (> 3%)"
    assert skel.sum() > 0


def test_width_within_1_pixel():
    """Verify that a crack of known thickness (5 px) is measured within 1 pixel error."""
    mask = np.zeros((80, 180), dtype=np.uint8)
    # Horizontal rectangle of thickness 5 pixels, length 80 pixels
    mask[35:40, 50:130] = 1

    results, _ = measure_crack(mask, min_area_px=20)
    measured_width = results["avg_width_px"]
    true_width = 5.0

    abs_error = abs(measured_width - true_width)
    assert abs_error <= 1.0, f"Width {measured_width:.2f} px deviates by {abs_error:.2f} px (> 1.0 px)"


def test_empty_mask_works():
    """Verify that an empty mask returns zeroed metrics and a descriptive note with no crash."""
    empty_mask = np.zeros((100, 100), dtype=np.uint8)
    results, skel = measure_crack(empty_mask)

    assert results["length_px"] == 0.0
    assert results["avg_width_px"] == 0.0
    assert results["max_width_px"] == 0.0
    assert results["p95_width_px"] == 0.0
    assert results["area_px"] == 0
    assert results["density_percent"] == 0.0
    assert results["num_components"] == 0
    assert results["num_branch_points"] == 0
    assert results["num_end_points"] == 0
    assert "Empty" in results["note"]
    assert skel.sum() == 0


def test_mm_is_none_without_scale():
    """Verify that metric (mm) measurements remain None when no mm_per_pixel scale is supplied."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[45:50, 20:80] = 1

    results, _ = measure_crack(mask, mm_per_pixel=None)
    assert results["length_mm"] is None
    assert results["avg_width_mm"] is None
    assert results["max_width_mm"] is None
    assert results["uncertainty_mm"] is None


def test_mm_appears_with_scale():
    """Verify that metric (mm) measurements and uncertainty are computed when scale is provided."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[45:50, 20:80] = 1

    scale = 0.20  # 0.20 mm per pixel
    results, _ = measure_crack(mask, mm_per_pixel=scale)

    assert results["length_mm"] is not None
    assert results["avg_width_mm"] is not None
    assert results["max_width_mm"] is not None
    assert results["uncertainty_mm"] is not None

    expected_len_mm = round(results["length_px"] * scale, 3)
    assert abs(results["length_mm"] - expected_len_mm) < 1e-3
    assert abs(results["uncertainty_mm"] - round(1.0 * scale, 3)) < 1e-3


def test_two_components_counted():
    """Verify that two spatially separated crack components are correctly identified and counted."""
    mask = np.zeros((140, 140), dtype=np.uint8)
    # Component 1: 5x50 = 250 px
    mask[25:30, 20:70] = 1
    # Component 2: 5x50 = 250 px
    mask[85:90, 20:70] = 1

    results, _ = measure_crack(mask, min_area_px=20)
    assert results["num_components"] == 2
