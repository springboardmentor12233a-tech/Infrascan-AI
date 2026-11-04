"""InfraScan Crack Geometry Measurement Module.

Provides deterministic, pixel-level morphological measurement of crack geometry
from 2D binary masks:
- Noise filtration via configurable connected-component area thresholding.
- Morphological centerline skeletonization via Zhang-Suen / Lee algorithm.
- Exact skeleton graph length using 8-connected Euclidean step summation
  (1.0 for orthogonal links, sqrt(2) for diagonal links, counted once per link).
- Local crack thickness via Euclidean Distance Transform along the skeleton.
- Dominant orientation angle (0 to 180 degrees) via Principal Component Analysis (PCA).
- Topological structure analysis: components, branch points, and endpoints.
- Optional physical unit scaling (mm) with uncertainty estimation.
- Graceful handling of empty or disconnected masks without runtime exceptions.
"""

from typing import Any, Dict, Optional, Tuple, Union
import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt
from skimage.morphology import skeletonize


def measure_crack(
    mask: np.ndarray,
    mm_per_pixel: Optional[float] = None,
    min_area_px: int = 20,
    width_mode: str = "edt2",
) -> Tuple[Dict[str, Any], np.ndarray]:
    """Measure morphological and geometric properties of cracks from a 2D binary mask.

    Parameters
    ----------
    mask : np.ndarray
        2D array of crack pixels. Any pixel with value > 0 is treated as crack.
    mm_per_pixel : Optional[float], default=None
        Physical resolution scale factor in millimeters per pixel. If provided,
        length_mm, avg_width_mm, max_width_mm, and uncertainty_mm are computed.
        If None, all metric millimeter fields are None.
    min_area_px : int, default=20
        Minimum connected component area in pixels. Components smaller than this
        are removed as high-frequency segmentation noise before measurement.
    width_mode : str, default="edt2"
        Formulation for calculating local crack caliper width:
        - "edt2": 2.0 * EDT (standard maximal inscribed circle diameter, default).
        - "edt2_minus1": 2.0 * EDT - 1.0, clipped at minimum 1.0.

    Returns
    -------
    Tuple[Dict[str, Any], np.ndarray]
        - results_dict: dictionary containing all measured geometric parameters.
        - skeleton_image: 2D uint8 binary image (0 or 1) of the morphological skeleton.
    """
    if mask is None:
        raise ValueError("Input mask cannot be None.")

    if width_mode not in ("edt2", "edt2_minus1"):
        raise ValueError(f"Unknown width_mode: '{width_mode}'. Must be 'edt2' or 'edt2_minus1'.")

    mask_arr = np.asarray(mask)
    if mask_arr.ndim != 2:
        raise ValueError(f"Input mask must be a 2D array, got shape {mask_arr.shape}")

    h, w = mask_arr.shape
    total_pixels = h * w
    bin_mask = (mask_arr > 0).astype(np.uint8)

    # Empty mask base results
    def _create_empty_result(note: str) -> Dict[str, Any]:
        res = {
            "length_px": 0.0,
            "avg_width_px": 0.0,
            "max_width_px": 0.0,
            "p95_width_px": 0.0,
            "area_px": 0,
            "density_percent": 0.0,
            "orientation_deg": 0.0,
            "num_components": 0,
            "num_branch_points": 0,
            "num_end_points": 0,
            "length_mm": 0.0 if (mm_per_pixel is not None and mm_per_pixel > 0) else None,
            "avg_width_mm": 0.0 if (mm_per_pixel is not None and mm_per_pixel > 0) else None,
            "max_width_mm": 0.0 if (mm_per_pixel is not None and mm_per_pixel > 0) else None,
            "uncertainty_mm": float(1.0 * mm_per_pixel) if (mm_per_pixel is not None and mm_per_pixel > 0) else None,
            "note": note,
        }
        return res

    skeleton_empty = np.zeros((h, w), dtype=np.uint8)

    if bin_mask.sum() == 0:
        return _create_empty_result("Empty mask: no crack pixels detected."), skeleton_empty

    # 1. Connected components analysis & noise filtration
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bin_mask, connectivity=8)
    cleaned_mask = np.zeros_like(bin_mask)
    valid_component_count = 0

    for lbl in range(1, num_labels):
        comp_area = stats[lbl, cv2.CC_STAT_AREA]
        if comp_area >= min_area_px:
            cleaned_mask[labels == lbl] = 1
            valid_component_count += 1

    area_px = int(cleaned_mask.sum())
    if area_px == 0:
        return _create_empty_result(
            f"All components smaller than min_area_px ({min_area_px} px) and filtered out."
        ), skeleton_empty

    density_percent = float(area_px / total_pixels * 100.0)

    # 2. Skeletonization
    skel_bool = skeletonize(cleaned_mask.astype(bool))
    skeleton = skel_bool.astype(np.uint8)
    skel_pixels = int(skeleton.sum())

    if skel_pixels == 0:
        return _create_empty_result("Skeletonization produced empty skeleton."), skeleton_empty

    # 3. Skeleton Length Calculation
    # Undirected step sum counting each link once:
    # Orthogonal links (horizontal or vertical) = 1.0
    # Diagonal links (down-right or down-left) = sqrt(2)
    n_h = int(np.sum(skel_bool[:, :-1] & skel_bool[:, 1:]))
    n_v = int(np.sum(skel_bool[:-1, :] & skel_bool[1:, :]))
    n_dr = int(np.sum(skel_bool[:-1, :-1] & skel_bool[1:, 1:]))
    n_dl = int(np.sum(skel_bool[:-1, 1:] & skel_bool[1:, :-1]))

    length_px = float((n_h + n_v) * 1.0 + (n_dr + n_dl) * np.sqrt(2.0))

    # If single isolated pixel with 0 links, length is 0.0
    # (or length_px is correctly 0.0)

    # 4. Width Estimation via Distance Transform along Skeleton
    # Distance to nearest background pixel (value 0)
    dt = distance_transform_edt(cleaned_mask.astype(bool))
    if width_mode == "edt2":
        widths = 2.0 * dt[skel_bool]
    else:  # "edt2_minus1"
        widths = np.maximum(2.0 * dt[skel_bool] - 1.0, 1.0)

    if len(widths) > 0:
        avg_width_px = float(np.mean(widths))
        max_width_px = float(np.max(widths))
        p95_width_px = float(np.percentile(widths, 95))
    else:
        avg_width_px = 0.0
        max_width_px = 0.0
        p95_width_px = 0.0

    # 5. Dominant Orientation (PCA on skeleton coordinates)
    skel_ys, skel_xs = np.where(skel_bool)
    if len(skel_xs) >= 2:
        pts = np.column_stack([skel_xs.astype(np.float64), skel_ys.astype(np.float64)])
        pts_centered = pts - np.mean(pts, axis=0)
        cov = np.cov(pts_centered, rowvar=False)

        if cov.shape == (2, 2) and np.isfinite(cov).all():
            eigenvalues, eigenvectors = np.linalg.eigh(cov)
            leading_vec = eigenvectors[:, np.argmax(eigenvalues)]  # [vx, vy]
            angle_rad = np.arctan2(leading_vec[1], leading_vec[0])
            orientation_deg = float(np.degrees(angle_rad) % 180.0)
        else:
            orientation_deg = 0.0
    else:
        orientation_deg = 0.0

    # 6. Branch Points and End Points Analysis
    # 8-connectivity neighborhood convolution
    neighbor_kernel = np.array([
        [1, 1, 1],
        [1, 0, 1],
        [1, 1, 1]
    ], dtype=np.uint8)

    neighbor_counts = cv2.filter2D(skeleton, -1, neighbor_kernel, borderType=cv2.BORDER_CONSTANT)

    # Filter only at skeleton pixels
    skel_neighbor_counts = neighbor_counts[skel_bool]
    num_branch_points = int(np.sum(skel_neighbor_counts >= 3))
    num_end_points = int(np.sum(skel_neighbor_counts == 1))

    # 7. Metric conversion if scale (mm_per_pixel) is provided
    if mm_per_pixel is not None and mm_per_pixel > 0:
        scale = float(mm_per_pixel)
        length_mm = float(length_px * scale)
        avg_width_mm = float(avg_width_px * scale)
        max_width_mm = float(max_width_px * scale)
        uncertainty_mm = float(1.0 * scale)
    else:
        length_mm = None
        avg_width_mm = None
        max_width_mm = None
        uncertainty_mm = None

    results = {
        "length_px": round(length_px, 3),
        "avg_width_px": round(avg_width_px, 3),
        "max_width_px": round(max_width_px, 3),
        "p95_width_px": round(p95_width_px, 3),
        "area_px": area_px,
        "density_percent": round(density_percent, 4),
        "orientation_deg": round(orientation_deg, 2),
        "num_components": valid_component_count,
        "num_branch_points": num_branch_points,
        "num_end_points": num_end_points,
        "length_mm": round(length_mm, 3) if length_mm is not None else None,
        "avg_width_mm": round(avg_width_mm, 3) if avg_width_mm is not None else None,
        "max_width_mm": round(max_width_mm, 3) if max_width_mm is not None else None,
        "uncertainty_mm": round(uncertainty_mm, 3) if uncertainty_mm is not None else None,
        "note": "Valid crack geometry measured.",
    }

    return results, skeleton

