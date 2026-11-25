"""Severity Stability Check Script.

Evaluates advisory damage severity consistency between ground truth annotated masks
and model predicted masks on the 1,087 Crack500 test images.

Applies scale-free factors a to c (crack_density_percent, relative_length, branching).
Measures algorithmic robustness to segmentation noise; this is NOT agreement with
expert civil engineering annotations.
"""

import csv
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add backend directory to Python path
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import cv2
import numpy as np

from app.ai.geometry import measure_crack
from app.services.severity_service import SEVERITY_ORDER, SEVERITY_RANK

MANIFEST_PATH = Path(r"D:\Infosys springboards\data\processed\manifests\crack500.csv")
PRED_MASKS_DIR = Path(
    r"D:\Infosys springboards\infrascan\ml\models\segmentation\unetplusplus_crack500\evaluation\crack500\masks"
)
CACHE_CSV_PATH = Path(
    r"D:\Infosys springboards\infrascan\ml\models\segmentation\unetplusplus_crack500\evaluation\annotated_geometry_cache.csv"
)


def score_scale_free(
    density_percent: float,
    length_px: float,
    num_branch_points: int,
    num_components: int,
    img_w: float,
    img_h: float,
) -> Tuple[float, str]:
    """Calculate scale-free severity score using factors a, b, and c."""
    diag = math.sqrt(img_w ** 2 + img_h ** 2) if (img_w > 0 and img_h > 0) else 1.0

    # Factor a: Crack Density
    if density_percent < 0.5:
        pts_a = 0.0
    elif density_percent < 2.0:
        pts_a = 10.0
    elif density_percent < 5.0:
        pts_a = 20.0
    elif density_percent < 10.0:
        pts_a = 30.0
    else:
        pts_a = 40.0

    # Factor b: Relative Length
    rel_len = (length_px / diag) if diag > 0 else 0.0
    if rel_len < 0.1:
        pts_b = 0.0
    elif rel_len < 0.3:
        pts_b = 5.0
    elif rel_len < 0.6:
        pts_b = 10.0
    elif rel_len < 1.0:
        pts_b = 15.0
    else:
        pts_b = 20.0

    # Factor c: Branching
    rate = ((num_branch_points / length_px) * 1000.0) if length_px > 0 else 0.0
    if rate < 2.0:
        base_c = 0.0
    elif rate < 5.0:
        base_c = 3.0
    else:
        base_c = 6.0

    bonus_c = 2.0 if num_components >= 3 else 0.0
    pts_c = min(8.0, base_c + bonus_c)

    score = min(100.0, pts_a + pts_b + pts_c)

    if score < 10.0:
        level = "none"
    elif score < 30.0:
        level = "minor"
    elif score < 55.0:
        level = "moderate"
    elif score < 80.0:
        level = "severe"
    else:
        level = "critical"

    return score, level


def quadratic_weighted_kappa(y_true: List[int], y_pred: List[int], num_classes: int = 5) -> float:
    """Compute Cohen's quadratic weighted kappa."""
    n = len(y_true)
    if n == 0:
        return 0.0

    conf_mat = np.zeros((num_classes, num_classes), dtype=np.float64)
    for t, p in zip(y_true, y_pred):
        conf_mat[t, p] += 1.0

    row_totals = conf_mat.sum(axis=1)
    col_totals = conf_mat.sum(axis=0)
    expected = np.outer(row_totals, col_totals) / n

    weights = np.zeros((num_classes, num_classes), dtype=np.float64)
    denom = (num_classes - 1) ** 2
    for i in range(num_classes):
        for j in range(num_classes):
            weights[i, j] = ((i - j) ** 2) / denom

    num = np.sum(weights * conf_mat)
    den = np.sum(weights * expected)

    if den == 0:
        return 1.0
    return 1.0 - (num / den)


def run_stability_check():
    print("=" * 70)
    print("  INFRA-SCAN DAMAGE SEVERITY STABILITY CHECK (Crack500 Test Split)")
    print("=" * 70)
    print("Notice: This analysis measures algorithmic robustness to segmentation")
    print("errors and model perturbations. It is NOT agreement with expert annotations.")
    print("Thresholds MUST NOT be tuned using these test split results.")
    print("=" * 70)

    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}")

    # 1. Read test manifest
    test_items = []
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("split") == "test":
                test_items.append(row)

    n_test = len(test_items)
    print(f"Loaded {n_test} test images from {MANIFEST_PATH}")

    # 2. Check for cache or compute annotated geometries
    annotated_geom: Dict[str, dict] = {}
    if CACHE_CSV_PATH.is_file():
        print(f"Loading cached annotated geometry from {CACHE_CSV_PATH}")
        with open(CACHE_CSV_PATH, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                stem = row["stem"]
                annotated_geom[stem] = {
                    "density_percent": float(row["density_percent"]),
                    "length_px": float(row["length_px"]),
                    "num_branch_points": int(row["num_branch_points"]),
                    "num_components": int(row["num_components"]),
                    "w": float(row["width"]),
                    "h": float(row["height"]),
                }
    else:
        print("Computing geometry on annotated masks (one-time calculation)...")
        cache_rows = []
        for idx, item in enumerate(test_items):
            m_path = Path(item["mask_path"])
            stem = m_path.stem
            mask = cv2.imread(str(m_path), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                continue
            h, w = mask.shape[:2]
            res, _ = measure_crack(mask, width_mode="edt2")
            annotated_geom[stem] = {
                "density_percent": res["density_percent"],
                "length_px": res["length_px"],
                "num_branch_points": res["num_branch_points"],
                "num_components": res["num_components"],
                "w": w,
                "h": h,
            }
            cache_rows.append({
                "stem": stem,
                "density_percent": res["density_percent"],
                "length_px": res["length_px"],
                "num_branch_points": res["num_branch_points"],
                "num_components": res["num_components"],
                "width": w,
                "height": h,
            })
            if (idx + 1) % 200 == 0 or (idx + 1) == n_test:
                print(f"  Processed {idx + 1}/{n_test} annotated masks...")

        try:
            with open(CACHE_CSV_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["stem", "density_percent", "length_px", "num_branch_points", "num_components", "width", "height"]
                )
                writer.writeheader()
                writer.writerows(cache_rows)
            print(f"Saved annotated geometry cache to {CACHE_CSV_PATH}")
        except Exception as e:
            print(f"Warning: could not write cache: {e}")

    # 3. Check for precomputed predicted geometry or compute from predicted masks
    pred_geom_csv = PRED_MASKS_DIR.parent / "geometry_results.csv"
    pred_geom: Dict[str, dict] = {}

    if pred_geom_csv.is_file():
        print(f"Loading predicted geometry from {pred_geom_csv}")
        with open(pred_geom_csv, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                stem = row["stem"]
                pred_geom[stem] = {
                    "density_percent": float(row["density_percent"]),
                    "length_px": float(row["length_px"]),
                    "num_branch_points": int(row["num_branch_points"]),
                    "num_components": int(row["num_components"]),
                }
    else:
        print(f"Computing geometry from predicted masks in {PRED_MASKS_DIR}...")
        for idx, item in enumerate(test_items):
            stem = Path(item["mask_path"]).stem
            p_file = PRED_MASKS_DIR / f"{stem}.png"
            if not p_file.is_file():
                continue
            mask = cv2.imread(str(p_file), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                continue
            res, _ = measure_crack(mask, width_mode="edt2")
            pred_geom[stem] = {
                "density_percent": res["density_percent"],
                "length_px": res["length_px"],
                "num_branch_points": res["num_branch_points"],
                "num_components": res["num_components"],
            }

    # 4. Compare Annotated vs Predicted
    ann_levels: List[str] = []
    pred_levels: List[str] = []
    ann_ranks: List[int] = []
    pred_ranks: List[int] = []

    # Perturbations
    pred_plus20_levels: List[str] = []
    pred_minus20_levels: List[str] = []

    for item in test_items:
        stem = Path(item["mask_path"]).stem
        if stem not in annotated_geom or stem not in pred_geom:
            continue

        a = annotated_geom[stem]
        p = pred_geom[stem]

        w, h = a["w"], a["h"]

        _, a_lvl = score_scale_free(
            density_percent=a["density_percent"],
            length_px=a["length_px"],
            num_branch_points=a["num_branch_points"],
            num_components=a["num_components"],
            img_w=w,
            img_h=h,
        )

        _, p_lvl = score_scale_free(
            density_percent=p["density_percent"],
            length_px=p["length_px"],
            num_branch_points=p["num_branch_points"],
            num_components=p["num_components"],
            img_w=w,
            img_h=h,
        )

        # +20% density
        _, p_plus = score_scale_free(
            density_percent=p["density_percent"] * 1.20,
            length_px=p["length_px"],
            num_branch_points=p["num_branch_points"],
            num_components=p["num_components"],
            img_w=w,
            img_h=h,
        )

        # -20% density
        _, p_minus = score_scale_free(
            density_percent=p["density_percent"] * 0.80,
            length_px=p["length_px"],
            num_branch_points=p["num_branch_points"],
            num_components=p["num_components"],
            img_w=w,
            img_h=h,
        )

        ann_levels.append(a_lvl)
        pred_levels.append(p_lvl)
        ann_ranks.append(SEVERITY_RANK[a_lvl])
        pred_ranks.append(SEVERITY_RANK[p_lvl])
        pred_plus20_levels.append(p_plus)
        pred_minus20_levels.append(p_minus)

    total_evaluated = len(ann_levels)

    # Distributions
    dist_ann = {k: ann_levels.count(k) for k in SEVERITY_ORDER}
    dist_pred = {k: pred_levels.count(k) for k in SEVERITY_ORDER}

    # Agreement
    exact_matches = sum(1 for a, p in zip(ann_ranks, pred_ranks) if a == p)
    within_one = sum(1 for a, p in zip(ann_ranks, pred_ranks) if abs(a - p) <= 1)

    exact_pct = (exact_matches / total_evaluated * 100.0) if total_evaluated else 0.0
    within_one_pct = (within_one / total_evaluated * 100.0) if total_evaluated else 0.0

    qwk = quadratic_weighted_kappa(ann_ranks, pred_ranks, num_classes=len(SEVERITY_ORDER))

    # Confusion matrix
    conf_mat = np.zeros((len(SEVERITY_ORDER), len(SEVERITY_ORDER)), dtype=int)
    for a, p in zip(ann_ranks, pred_ranks):
        conf_mat[a, p] += 1

    # Perturbation analysis
    change_plus20 = sum(1 for p, pp in zip(pred_levels, pred_plus20_levels) if p != pp)
    change_minus20 = sum(1 for p, pm in zip(pred_levels, pred_minus20_levels) if p != pm)

    # 5. Output Report
    print("\n--- 1. SEVERITY DISTRIBUTION ---")
    print(f"{'Severity Level':<12} | {'Annotated Masks':<18} | {'Predicted Masks':<18}")
    print("-" * 54)
    for lvl in SEVERITY_ORDER:
        c_a = dist_ann[lvl]
        c_p = dist_pred[lvl]
        pct_a = (c_a / total_evaluated * 100.0) if total_evaluated else 0.0
        pct_p = (c_p / total_evaluated * 100.0) if total_evaluated else 0.0
        print(f"{lvl:<12} | {c_a:>5} ({pct_a:>5.1f}%)      | {c_p:>5} ({pct_p:>5.1f}%)")

    print("\n--- 2. AGREEMENT METRICS ---")
    print(f"Total Evaluated Images:       {total_evaluated}")
    print(f"Exact Agreement:              {exact_matches}/{total_evaluated} ({exact_pct:.2f}%)")
    print(f"Agreement Within 1 Level:     {within_one}/{total_evaluated} ({within_one_pct:.2f}%)")
    print(f"Quadratic Weighted Kappa:     {qwk:.4f}")

    print("\n--- 3. CONFUSION MATRIX (Rows: Annotated, Columns: Predicted) ---")
    hdr = f"{'Annotated':<12} | " + " | ".join(f"{lvl:>8}" for lvl in SEVERITY_ORDER)
    print(hdr)
    print("-" * len(hdr))
    for i, row_lvl in enumerate(SEVERITY_ORDER):
        row_str = f"{row_lvl:<12} | " + " | ".join(f"{conf_mat[i, j]:>8}" for j in range(len(SEVERITY_ORDER)))
        print(row_str)

    print("\n--- 4. SENSITIVITY TO DENSITY PERTURBATION (+-20%) ---")
    print(f"+20% density perturbation band changes: {change_plus20}/{total_evaluated} ({change_plus20/total_evaluated*100.0:.2f}%)")
    print(f"-20% density perturbation band changes: {change_minus20}/{total_evaluated} ({change_minus20/total_evaluated*100.0:.2f}%)")
    print("=" * 70)


if __name__ == "__main__":
    run_stability_check()

