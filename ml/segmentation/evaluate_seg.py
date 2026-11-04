"""InfraScan Crack Segmentation Evaluation Suite.

Provides standardized, leak-free evaluation for crack segmentation models:
- Image-level and overall (pixel-pooled) metrics: Dice, IoU, Precision, Recall, Specificity, Pixel Accuracy, Boundary F1 (3px tolerance).
- Single-run test guard preventing test split data snooping (FORCE_RERUN check).
- Non-parametric bootstrap 95% confidence intervals (500 resamples, seed 42) for Dice and IoU.
- Crack width error analysis (thin, medium, thick bins via Euclidean distance transform).
- Inference speed and SLA benchmark (model size in MB, GPU latency per image).
- High-resolution artifact generation: 24 qualitative 4-panel comparison figures (image, true mask, prediction, overlay).
- Export binary predicted masks (0/255 PNG) for downstream structural engineering tasks (Task 6).
"""

import datetime
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.segmentation import config
from ml.segmentation.train_seg import CrackSegDataset, build_model


def compute_boundary_f1(pred_bin: np.ndarray, gt_bin: np.ndarray, tolerance: int = config.BOUNDARY_TOLERANCE_PX) -> float:
    """Compute Boundary F1 score (BF-score) with morphological dilation and distance transform."""
    p = pred_bin.astype(np.uint8)
    g = gt_bin.astype(np.uint8)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    p_bound = cv2.dilate(p, kernel) - p
    g_bound = cv2.dilate(g, kernel) - g

    n_p = int(p_bound.sum())
    n_g = int(g_bound.sum())

    if n_p == 0 and n_g == 0:
        return 1.0
    if n_p == 0 or n_g == 0:
        return 0.0

    # Distance to boundaries (distanceTransform computes distance to nearest 0-pixel)
    dist_to_g = cv2.distanceTransform(1 - g_bound, cv2.DIST_L2, 3)
    dist_to_p = cv2.distanceTransform(1 - p_bound, cv2.DIST_L2, 3)

    p_precision = float((dist_to_g[p_bound > 0] <= tolerance).sum()) / n_p
    g_recall = float((dist_to_p[g_bound > 0] <= tolerance).sum()) / n_g

    if (p_precision + g_recall) <= 1e-7:
        return 0.0
    return float(2.0 * p_precision * g_recall / (p_precision + g_recall))


def estimate_crack_width(gt_bin: np.ndarray) -> float:
    """Estimate crack width in pixels using Euclidean distance transform along crack centerline."""
    if gt_bin.sum() == 0:
        return 0.0
    dt = cv2.distanceTransform(gt_bin.astype(np.uint8), cv2.DIST_L2, 5)
    # The maximum distance to boundary is the inradius (half-width), so width = 2 * inradius
    max_half_width = float(dt.max())
    return 2.0 * max_half_width


def compute_bootstrap_confidence_intervals(
    scores: List[float],
    n_resamples: int = config.BOOTSTRAP_RESAMPLES,
    seed: int = config.BOOTSTRAP_SEED,
) -> Dict[str, Any]:
    """Compute non-parametric 95% bootstrap confidence intervals over image-level scores."""
    if not scores:
        return {"mean": 0.0, "ci_95": [0.0, 0.0]}

    rng = np.random.RandomState(seed)
    scores_arr = np.array(scores)
    n = len(scores_arr)

    boot_means = []
    for _ in range(n_resamples):
        sample = rng.choice(scores_arr, size=n, replace=True)
        boot_means.append(float(np.mean(sample)))

    return {
        "mean": round(float(np.mean(boot_means)), 4),
        "ci_95": [
            round(float(np.percentile(boot_means, 2.5)), 4),
            round(float(np.percentile(boot_means, 97.5)), 4),
        ],
    }


def benchmark_inference_speed_and_size(
    model: nn.Module,
    checkpoint_path: str,
    device: torch.device,
    input_size: Tuple[int, int] = (384, 384),
    warmup_runs: int = config.SPEED_WARMUP_RUNS,
    timed_runs: int = config.SPEED_TIMED_RUNS,
) -> Dict[str, Any]:
    """Benchmark model checkpoint size (MB) and single-image GPU latency."""
    file_size_mb = 0.0
    if os.path.exists(checkpoint_path):
        file_size_mb = round(os.path.getsize(checkpoint_path) / (1024 * 1024), 2)

    model.eval()
    dummy_input = torch.zeros((1, 3, input_size[0], input_size[1]), device=device)
    is_cuda = device.type == "cuda"

    # Warmup
    with torch.no_grad():
        for _ in range(warmup_runs):
            _ = model(dummy_input)
            if is_cuda:
                torch.cuda.synchronize()

    # Timed runs
    latencies_ms = []
    with torch.no_grad():
        for _ in range(timed_runs):
            t0 = time.perf_counter()
            _ = model(dummy_input)
            if is_cuda:
                torch.cuda.synchronize()
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)

    mean_lat = float(np.mean(latencies_ms))
    p50_lat = float(np.median(latencies_ms))
    p95_lat = float(np.percentile(latencies_ms, 95))

    return {
        "model_file_size_mb": file_size_mb,
        "single_image_latency_ms": {
            "mean": round(mean_lat, 2),
            "p50": round(p50_lat, 2),
            "p95": round(p95_lat, 2),
        },
        "fps": round(1000.0 / mean_lat, 2) if mean_lat > 0 else 0.0,
    }


def create_visualization_panel(
    img_rgb: np.ndarray,
    gt_bin: np.ndarray,
    pred_bin: np.ndarray,
) -> np.ndarray:
    """Create a 4-panel visual comparison: Image | Ground Truth | Prediction | Color Overlay."""
    h, w = gt_bin.shape[:2]

    # Normalize image to [0, 255] uint8
    if img_rgb.max() <= 1.0:
        display_img = (img_rgb * 255.0).astype(np.uint8)
    else:
        display_img = img_rgb.astype(np.uint8)

    # 1. Image panel
    p1 = cv2.resize(display_img, (w, h))

    # 2. GT mask panel (white crack on black)
    p2 = np.repeat((gt_bin * 255.0).astype(np.uint8)[:, :, np.newaxis], 3, axis=2)

    # 3. Pred mask panel (white crack on black)
    p3 = np.repeat((pred_bin * 255.0).astype(np.uint8)[:, :, np.newaxis], 3, axis=2)

    # 4. Color Overlay panel: TP = Green, FP = Red, FN = Yellow
    overlay = display_img.copy()
    tp_mask = (pred_bin == 1) & (gt_bin == 1)
    fp_mask = (pred_bin == 1) & (gt_bin == 0)
    fn_mask = (pred_bin == 0) & (gt_bin == 1)

    overlay[tp_mask] = [0, 255, 0]      # Green = True Positive
    overlay[fp_mask] = [255, 0, 0]      # Red = False Positive
    overlay[fn_mask] = [255, 255, 0]    # Yellow = False Negative

    p4 = cv2.addWeighted(display_img, 0.45, overlay, 0.55, 0)

    # Stack horizontally: [Image | GT | Pred | Overlay]
    panel = np.hstack([p1, p2, p3, p4])
    return panel


def test_once(
    model_or_weights: Any,
    threshold: float,
    split: str,
    manifest_csv: str,
    output_dir: Optional[str] = None,
    data_root: str = "",
    force_rerun: bool = config.FORCE_RERUN,
    device_str: str = "cuda:0",
) -> Dict[str, Any]:
    """Evaluate crack segmentation model on a test split exactly once with single-run guard protection.

    Refuses to re-run if <output_dir>/test_metrics_<split>.json exists unless force_rerun=True.
    """
    device = torch.device(device_str if torch.cuda.is_available() else "cpu")

    # Determine run output directory
    if output_dir is None:
        if isinstance(model_or_weights, (str, Path)) and os.path.exists(str(model_or_weights)):
            out_path = Path(model_or_weights).parent
        else:
            out_path = Path("evaluation")
    else:
        out_path = Path(output_dir)

    out_path.mkdir(parents=True, exist_ok=True)
    metrics_json_path = out_path / f"test_metrics_{split}.json"

    # Single-run guard
    if metrics_json_path.exists() and not force_rerun:
        print("=" * 70)
        print(f"[TEST GUARD ACTIVE] Metrics already exist for split '{split}' at: {metrics_json_path}")
        print("Refusing to re-run test evaluation to prevent test split data snooping.")
        print("Set FORCE_RERUN=True only if you explicitly intend to overwrite test results.")
        print("=" * 70)
        with open(metrics_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Load model
    if isinstance(model_or_weights, (str, Path)):
        ckpt_path = str(model_or_weights)
        ckpt = torch.load(ckpt_path, map_location=device)
        # Determine model architecture from run card if available, else default to unet
        run_card = Path(ckpt_path).parent / "run_card.json"
        m_name = "unet"
        if run_card.exists():
            with open(run_card, "r") as rf:
                m_name = json.load(rf).get("model_name", "unet")
        model = build_model(model_name=m_name).to(device)
        model.load_state_dict(ckpt["model_state_dict"])
    else:
        model = model_or_weights
        ckpt_path = ""

    model.eval()

    # Load dataset
    df = pd.read_csv(manifest_csv)
    split_df = df[df["split"] == split].copy()
    if split_df.empty:
        raise ValueError(f"No samples found for split '{split}' in {manifest_csv}")

    dataset = CrackSegDataset(split_df, data_root=data_root, is_train=False)
    loader = DataLoader(
        dataset,
        batch_size=1,  # Full image inference
        shuffle=False,
        num_workers=0,
    )

    print("=" * 70)
    print(f"Running Protected Test Evaluation on '{split}' ({len(dataset):,} images)")
    print(f"  Operating Threshold : {threshold:.2f} (chosen on VALIDATION split only)")
    print(f"  Device              : {device}")
    print("=" * 70)

    # Directories for predicted masks and panels
    masks_dir = out_path / f"masks_{split}"
    masks_dir.mkdir(parents=True, exist_ok=True)
    vis_dir = out_path / f"visualizations_{split}"
    vis_dir.mkdir(parents=True, exist_ok=True)

    image_records = []
    total_tp = 0.0
    total_fp = 0.0
    total_fn = 0.0
    total_tn = 0.0

    empty_gt_count = 0
    candidate_panels: List[Tuple[float, np.ndarray, str]] = []  # (dice, panel_img, filename)

    for idx, (img_t, mask_t, orig_h_t, orig_w_t, rel_path_tuple) in enumerate(loader):
        img_t = img_t.to(device)
        orig_h = int(orig_h_t[0])
        orig_w = int(orig_w_t[0])
        rel_path = rel_path_tuple[0]
        fname = Path(rel_path).name

        with torch.no_grad():
            logits = model(img_t)
            probs = torch.sigmoid(logits)[0, 0, :orig_h, :orig_w].cpu().numpy()

        pred_bin = (probs >= threshold).astype(np.float32)
        gt_bin = mask_t[0, 0, :orig_h, :orig_w].numpy()

        # Save binary predicted mask as PNG (0 / 255) for Task 6
        pred_png = (pred_bin * 255.0).astype(np.uint8)
        mask_save_name = Path(fname).stem + "_pred.png"
        cv2.imwrite(str(masks_dir / mask_save_name), pred_png)

        # Image-level confusion counts
        tp = float((pred_bin * gt_bin).sum())
        fp = float((pred_bin * (1.0 - gt_bin)).sum())
        fn = float(((1.0 - pred_bin) * gt_bin).sum())
        tn = float(((1.0 - pred_bin) * (1.0 - gt_bin)).sum())

        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_tn += tn

        is_empty = (gt_bin.sum() == 0)
        if is_empty:
            empty_gt_count += 1

        # Metrics for image (skip empty masks in per-image mean)
        if not is_empty or pred_bin.sum() > 0:
            dice = (2.0 * tp + 1e-7) / (2.0 * tp + fp + fn + 1e-7)
            iou = (tp + 1e-7) / (tp + fp + fn + 1e-7)
            prec = (tp + 1e-7) / (tp + fp + 1e-7)
            rec = (tp + 1e-7) / (tp + fn + 1e-7)
            spec = (tn + 1e-7) / (tn + fp + 1e-7)
            acc = (tp + tn) / (tp + tn + fp + fn + 1e-7)
            b_f1 = compute_boundary_f1(pred_bin, gt_bin, tolerance=config.BOUNDARY_TOLERANCE_PX)
        else:
            dice = 1.0 if pred_bin.sum() == 0 else 0.0
            iou = 1.0 if pred_bin.sum() == 0 else 0.0
            prec = 1.0 if pred_bin.sum() == 0 else 0.0
            rec = 1.0
            spec = 1.0 if pred_bin.sum() == 0 else 0.0
            acc = 1.0
            b_f1 = 1.0

        crack_w = estimate_crack_width(gt_bin)

        record = {
            "image": fname,
            "is_empty_gt": is_empty,
            "crack_width_px": round(crack_w, 2),
            "dice": round(float(dice), 4),
            "iou": round(float(iou), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "specificity": round(float(spec), 4),
            "pixel_accuracy": round(float(acc), 4),
            "boundary_f1": round(float(b_f1), 4),
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "tn": int(tn),
        }
        image_records.append(record)

        # Prepare qualitative panel
        # De-normalize image for visualization
        unnorm_img = img_t[0, :, :orig_h, :orig_w].cpu().numpy().transpose(1, 2, 0)
        unnorm_img = unnorm_img * np.array(config.IMAGENET_STD) + np.array(config.IMAGENET_MEAN)
        unnorm_img = np.clip(unnorm_img * 255.0, 0, 255).astype(np.uint8)

        panel = create_visualization_panel(unnorm_img, gt_bin, pred_bin)
        candidate_panels.append((float(dice), panel, fname))

    # Calculate Summary Metrics
    # Filter out empty GT masks for per-image mean as requested
    non_empty_records = [r for r in image_records if not r["is_empty_gt"]]
    eval_pool = non_empty_records if non_empty_records else image_records

    per_image_means = {
        "dice": round(float(np.mean([r["dice"] for r in eval_pool])), 4),
        "iou": round(float(np.mean([r["iou"] for r in eval_pool])), 4),
        "precision": round(float(np.mean([r["precision"] for r in eval_pool])), 4),
        "recall_sensitivity": round(float(np.mean([r["recall"] for r in eval_pool])), 4),
        "specificity": round(float(np.mean([r["specificity"] for r in eval_pool])), 4),
        "pixel_accuracy": round(float(np.mean([r["pixel_accuracy"] for r in eval_pool])), 4),
        "boundary_f1": round(float(np.mean([r["boundary_f1"] for r in eval_pool])), 4),
        "images_evaluated_in_mean": len(eval_pool),
        "empty_gt_images_skipped": empty_gt_count,
    }

    # Overall (Pixel-Pooled) Values across entire split
    overall_dice = (2.0 * total_tp) / (2.0 * total_tp + total_fp + total_fn + 1e-7)
    overall_iou = total_tp / (total_tp + total_fp + total_fn + 1e-7)
    overall_prec = total_tp / (total_tp + total_fp + 1e-7)
    overall_rec = total_tp / (total_tp + total_fn + 1e-7)
    overall_spec = total_tn / (total_tn + total_fp + 1e-7)
    overall_acc = (total_tp + total_tn) / (total_tp + total_tn + total_fp + total_fn + 1e-7)

    pixel_pooled = {
        "overall_dice": round(float(overall_dice), 4),
        "overall_iou": round(float(overall_iou), 4),
        "overall_precision": round(float(overall_prec), 4),
        "overall_recall": round(float(overall_rec), 4),
        "overall_specificity": round(float(overall_spec), 4),
        "overall_pixel_accuracy": round(float(overall_acc), 4),
        "total_pixels_evaluated": int(total_tp + total_fp + total_fn + total_tn),
        "total_crack_pixels": int(total_tp + total_fn),
        "crack_pixel_share_pct": round(float((total_tp + total_fn) / (total_tp + total_fp + total_fn + total_tn) * 100), 2),
    }

    # Bootstrap 95% Confidence Intervals
    dice_scores = [r["dice"] for r in eval_pool]
    iou_scores = [r["iou"] for r in eval_pool]

    ci_dice = compute_bootstrap_confidence_intervals(dice_scores, config.BOOTSTRAP_RESAMPLES, config.BOOTSTRAP_SEED)
    ci_iou = compute_bootstrap_confidence_intervals(iou_scores, config.BOOTSTRAP_RESAMPLES, config.BOOTSTRAP_SEED)

    # Crack Width Breakdown (Thin, Medium, Thick)
    width_bins: Dict[str, Dict[str, Any]] = {
        "thin (<5px)": {"dices": [], "ious": [], "recalls": [], "count": 0},
        "medium (5-15px)": {"dices": [], "ious": [], "recalls": [], "count": 0},
        "thick (>15px)": {"dices": [], "ious": [], "recalls": [], "count": 0},
    }

    for r in non_empty_records:
        w = r["crack_width_px"]
        if w < config.WIDTH_THIN_MAX:
            category = "thin (<5px)"
        elif w <= config.WIDTH_MED_MAX:
            category = "medium (5-15px)"
        else:
            category = "thick (>15px)"

        width_bins[category]["dices"].append(r["dice"])
        width_bins[category]["ious"].append(r["iou"])
        width_bins[category]["recalls"].append(r["recall"])
        width_bins[category]["count"] += 1

    width_summary = {}
    for cat, bdata in width_bins.items():
        width_summary[cat] = {
            "image_count": bdata["count"],
            "mean_dice": round(float(np.mean(bdata["dices"])), 4) if bdata["count"] > 0 else 0.0,
            "mean_iou": round(float(np.mean(bdata["ious"])), 4) if bdata["count"] > 0 else 0.0,
            "mean_recall": round(float(np.mean(bdata["recalls"])), 4) if bdata["count"] > 0 else 0.0,
        }

    # Speed & Size Benchmark
    speed_info = benchmark_inference_speed_and_size(
        model=model,
        checkpoint_path=ckpt_path,
        device=device,
        input_size=(config.IMAGE_SIZE_TRAIN, config.IMAGE_SIZE_TRAIN),
    )

    # Save 24 Example Panels (8 Best, 8 Worst, 8 Median)
    candidate_panels.sort(key=lambda x: x[0])  # Sort by Dice ascending
    n_total = len(candidate_panels)
    selected_panels = []

    if n_total <= config.NUM_VISUALIZATION_PANELS:
        selected_panels = candidate_panels
    else:
        worst_8 = candidate_panels[:8]
        best_8 = candidate_panels[-8:]
        mid_start = (n_total - 8) // 2
        mid_8 = candidate_panels[mid_start : mid_start + 8]
        selected_panels = worst_8 + mid_8 + best_8

    for rank, (d_val, panel_img, fname) in enumerate(selected_panels):
        out_name = f"panel_{rank+1:02d}_dice_{d_val:.3f}_{Path(fname).stem}.png"
        cv2.imwrite(str(vis_dir / out_name), panel_img)

    print(f"[OK] Saved {len(selected_panels)} qualitative 4-panel figures to: {vis_dir}")
    print(f"[OK] Saved {len(image_records)} predicted binary masks to: {masks_dir}")

    # Compile Final JSON Report
    final_metrics = {
        "split": split,
        "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "checkpoint_evaluated": ckpt_path,
        "chosen_threshold": round(threshold, 2),
        "total_images": len(image_records),
        "empty_gt_images": empty_gt_count,
        "per_image_mean_metrics": per_image_means,
        "pixel_pooled_metrics": pixel_pooled,
        "bootstrap_95_ci": {
            "dice": ci_dice,
            "iou": ci_iou,
        },
        "performance_by_crack_width": width_summary,
        "speed_and_size_benchmark": speed_info,
    }

    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(final_metrics, f, indent=2)

    print(f"[OK] Saved test metrics to: {metrics_json_path}")
    print("\n--- Summary Performance on Split:", split, "---")
    print(f"  Per-Image Mean Dice : {per_image_means['dice']:.4f} (95% CI: {ci_dice['ci_95']})")
    print(f"  Per-Image Mean IoU  : {per_image_means['iou']:.4f} (95% CI: {ci_iou['ci_95']})")
    print(f"  Boundary F1 Score   : {per_image_means['boundary_f1']:.4f}")
    print(f"  Pixel-Pooled Dice   : {pixel_pooled['overall_dice']:.4f}")
    print(f"  Pixel-Pooled IoU    : {pixel_pooled['overall_iou']:.4f}")
    return final_metrics

