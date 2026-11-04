"""Crack Geometry Measurement on Clean Crack500 Manifest Test Split.

Strictly filters for split == 'test' in manifests/crack500.csv (1,087 clean test images),
reads winning model predicted masks (unetplusplus_crack500, threshold 0.40),
measures morphological crack geometry (length, width via edt2, orientation, components, branch/end points),
exports geometry_results.csv and geometry_summary.csv,
and generates 12 annotated inspection overlays.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
import pandas as pd

# Ensure infrascan directory is in sys.path
_infrascan_dir = Path(__file__).resolve().parent.parent.parent
if str(_infrascan_dir) not in sys.path:
    sys.path.insert(0, str(_infrascan_dir))

from ml.geometry.crack_geometry import measure_crack


def create_annotated_overlay(
    img_bgr: Optional[np.ndarray],
    mask: np.ndarray,
    skeleton: np.ndarray,
    res: Dict[str, Any],
) -> np.ndarray:
    """Create visual inspection overlay: original image, mask, red skeleton, metrics text."""
    h, w = mask.shape[:2]
    vis = img_bgr.copy() if img_bgr is not None else np.zeros((h, w, 3), dtype=np.uint8)
    if vis.shape[:2] != (h, w):
        vis = cv2.resize(vis, (w, h))

    # Translucent green crack mask overlay
    overlay = vis.copy()
    overlay[mask > 0] = [0, 220, 0]  # Green in BGR
    blended = cv2.addWeighted(vis, 0.65, overlay, 0.35, 0)

    # Bright RED skeleton (dilated 1px for high-res visibility)
    skel_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    skel_dil = cv2.dilate(skeleton.astype(np.uint8), skel_kernel)
    blended[skel_dil > 0] = [0, 0, 255]  # Red in BGR

    # Annotate metrics text banner
    len_txt = f"Length: {res['length_px']:.1f} px"
    wid_txt = f"Avg W: {res['avg_width_px']:.1f} px | Max W: {res['max_width_px']:.1f} px | p95: {res['p95_width_px']:.1f} px"
    comp_txt = f"Comps: {res['num_components']} | Branches: {res['num_branch_points']} | Ends: {res['num_end_points']} | Orient: {res['orientation_deg']:.1f} deg"

    # Draw semi-transparent header banner
    cv2.rectangle(blended, (0, 0), (w, 55), (20, 20, 20), -1)
    cv2.putText(blended, f"{len_txt}  |  {wid_txt}", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(blended, comp_txt, (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 240, 255), 1, cv2.LINE_AA)

    return blended


def main():
    print("=" * 80)
    print("INFRASCAN CRACK GEOMETRY MEASUREMENT (MANIFEST TEST SPLIT)")
    print("=" * 80)

    project_root = Path(r"d:\Infosys springboards\infrascan")
    data_root = Path(r"d:\Infosys springboards\data")
    manifest_csv = data_root / "processed" / "manifests" / "crack500.csv"
    winner_dir = project_root / "ml" / "models" / "segmentation" / "unetplusplus_crack500"
    masks_dir = winner_dir / "evaluation" / "crack500" / "masks"

    if not manifest_csv.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_csv}")
    if not masks_dir.exists():
        raise FileNotFoundError(f"Predicted masks directory not found: {masks_dir}")

    # 1. Read manifest and filter for test split only
    df_manifest = pd.read_csv(manifest_csv)
    df_test = df_manifest[df_manifest["split"] == "test"].reset_index(drop=True)
    manifest_test_count = len(df_test)
    print(f"Manifest test images (split == 'test'): {manifest_test_count}")

    # Output paths
    geometry_dir = project_root / "ml" / "geometry"
    geometry_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir = geometry_dir / "overlays"
    overlays_dir.mkdir(parents=True, exist_ok=True)

    # 2. Iterate through test split and measure
    results_records = []
    overlay_candidates = []
    mask_files_found = 0
    masks_measured = 0
    missing_failed = 0

    for idx, row in df_test.iterrows():
        img_path = Path(row["image_path"])
        stem = img_path.stem
        mask_path = masks_dir / f"{stem}.png"

        if not mask_path.exists():
            missing_failed += 1
            print(f"[MISSING] Mask not found for: {stem}")
            continue

        mask_files_found += 1
        mask_raw = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask_raw is None:
            missing_failed += 1
            print(f"[READ ERROR] Could not read mask: {mask_path}")
            continue

        # Measure with canonical width_mode="edt2"
        res, skel = measure_crack(mask_raw, min_area_px=20, width_mode="edt2")
        res["stem"] = stem
        res["mask_file"] = str(mask_path)
        results_records.append(res)
        masks_measured += 1

        if res["length_px"] > 0:
            overlay_candidates.append((res["length_px"], img_path, mask_raw, res, skel))

        if (idx + 1) % 200 == 0 or (idx + 1) == manifest_test_count:
            print(f"  Processed {idx + 1}/{manifest_test_count} test images...", flush=True)

    print("\n" + "=" * 60)
    print("VERIFICATION COUNTS:")
    print(f"  Manifest test images: {manifest_test_count}")
    print(f"  Mask files found:     {mask_files_found}")
    print(f"  Masks measured:       {masks_measured}")
    print(f"  Missing / failed:     {missing_failed}")
    print("=" * 60)

    # 3. Export geometry_results.csv
    df_results = pd.DataFrame(results_records)
    cols_order = [
        "stem", "length_px", "avg_width_px", "max_width_px", "p95_width_px",
        "area_px", "density_percent", "orientation_deg", "num_components",
        "num_branch_points", "num_end_points", "length_mm", "avg_width_mm",
        "max_width_mm", "uncertainty_mm", "note", "mask_file"
    ]
    cols_order = [c for c in cols_order if c in df_results.columns]
    df_results = df_results[cols_order]

    csv_out1 = geometry_dir / "geometry_results.csv"
    csv_out2 = winner_dir / "evaluation" / "geometry_results.csv"
    df_results.to_csv(csv_out1, index=False)
    df_results.to_csv(csv_out2, index=False)
    print(f"\n[OK] Geometry results exported to: {csv_out1}")

    # 4. Generate geometry_summary.csv
    numeric_cols = [
        "length_px", "avg_width_px", "max_width_px", "p95_width_px",
        "area_px", "density_percent", "orientation_deg", "num_components",
        "num_branch_points", "num_end_points"
    ]
    cracked_df = df_results[df_results["area_px"] > 0]
    if len(cracked_df) == 0:
        cracked_df = df_results

    summary_rows = []
    for col in numeric_cols:
        if col in cracked_df.columns:
            vals = cracked_df[col].dropna()
            summary_rows.append({
                "Metric": col,
                "Mean": round(float(vals.mean()), 2),
                "Median (p50)": round(float(vals.median()), 2),
                "95th Percentile (p95)": round(float(np.percentile(vals, 95)), 2),
            })

    df_summary = pd.DataFrame(summary_rows)
    sum_csv1 = geometry_dir / "geometry_summary.csv"
    sum_csv2 = winner_dir / "evaluation" / "geometry_summary.csv"
    df_summary.to_csv(sum_csv1, index=False)
    df_summary.to_csv(sum_csv2, index=False)

    print("\n" + "=" * 75)
    print("GEOMETRY DISTRIBUTION SUMMARY TABLE (CRACKED SAMPLES, N = %d)" % len(cracked_df))
    print("=" * 75)
    print(df_summary.to_string(index=False))
    print("=" * 75)

    # 5. Generate 12 inspection overlays
    # Clear any old overlays in directory first
    for f in overlays_dir.glob("overlay_*.png"):
        try:
            f.unlink()
        except Exception:
            pass

    overlay_candidates.sort(key=lambda x: x[0])
    selected_indices = np.linspace(0, max(0, len(overlay_candidates) - 1), 12, dtype=int)
    saved_overlays = 0

    print(f"\n[OVERLAYS] Generating 12 visual inspection overlays in: {overlays_dir}")
    for idx_num, sel_idx in enumerate(selected_indices, 1):
        if sel_idx >= len(overlay_candidates):
            break
        _, img_path, mask_raw, res, skel = overlay_candidates[sel_idx]
        stem = res["stem"]

        img_bgr = cv2.imread(str(img_path)) if (img_path and img_path.exists()) else None
        overlay_img = create_annotated_overlay(img_bgr, mask_raw, skel, res)

        out_fn = overlays_dir / f"overlay_{idx_num:02d}_{stem}.png"
        cv2.imwrite(str(out_fn), overlay_img)
        saved_overlays += 1

    print(f"[OK] Successfully saved {saved_overlays} overlays to: {overlays_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()

