"""InfraScan YOLO Detection Evaluation and Benchmarking Suite.

Implements rigorous, leak-free evaluation for Ultralytics YOLO models on RDD2022:
- Validation mAP, AP50, AP50-95, and optimal F1 confidence threshold selection.
- Single-run test guard preventing test split data snooping (FORCE_RERUN check).
- Per-class and per-country performance breakdown.
- Image-level False Positive Rate (FPR) and False Negative Rate (FNR).
- Non-parametric bootstrap 95% confidence intervals (500 resamples, seed 42).
- 64-bit dHash near-duplicate train/test leakage audit using vectorized CPU LUT.
- Inference speed and SLA benchmark (batch 1 latency, batch 16 throughput, model size).
- High-resolution artifact visualizations (confusion matrix, PR/F1 curves, 24 qualitative crops).
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

from ml.detection import config

# Fast 256-element bit count lookup table for vectorized CPU Hamming distance
_BIT_COUNT_LUT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def get_country_from_filename(filename: str) -> str:
    """Extract country prefix from RDD2022 filename."""
    for c in config.COUNTRIES:
        if filename.startswith(c + "_"):
            return c
    return filename.split("_")[0]


def compute_dhash(img_path: str, hash_size: int = 8) -> int:
    """Compute 64-bit difference hash (dHash) for an image.

    Resizes to (hash_size + 1, hash_size) grayscale, compares horizontal adjacent pixels,
    and returns a 64-bit integer.
    """
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0
    resized = cv2.resize(img, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    packed = np.packbits(diff.flatten())
    return int.from_bytes(packed.tobytes(), byteorder="big")


def validate(
    model_or_weights: Any,
    data_yaml: str,
    split: str = "val",
    conf: float = config.VAL_CONF,
    iou: float = config.VAL_IOU,
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate YOLO model on the validation split and pick the optimal F1 threshold.

    Args:
        model_or_weights: Ultralytics YOLO model object or path to checkpoint .pt file.
        data_yaml: Path to data.yaml dataset configuration.
        split: Dataset split to evaluate ('val' or 'test').
        conf: Minimum confidence threshold (0.001 to capture full PR curve).
        iou: NMS IoU threshold (0.6 default).
        device: Torch device (e.g., '0' or 'cpu').

    Returns:
        Dictionary containing overall metrics, per-class metrics, curves, and chosen threshold.
    """
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise ImportError(
            "Ultralytics is required for validation. Install it via 'pip install ultralytics'."
        ) from e

    if isinstance(model_or_weights, str) or isinstance(model_or_weights, Path):
        model = YOLO(str(model_or_weights))
    else:
        model = model_or_weights

    print("=" * 70)
    print(f"Running Validation on '{split}' split (conf={conf}, iou={iou})...")
    print("=" * 70)

    val_kwargs = {
        "data": str(data_yaml),
        "split": split,
        "conf": conf,
        "iou": iou,
        "batch": config.BATCH_SIZE,
        "plots": True,
        "workers": config.WORKERS,
    }
    if device is not None:
        val_kwargs["device"] = device

    metrics = model.val(**val_kwargs)

    # Extract scalar metrics
    mp = float(metrics.box.mp) if hasattr(metrics.box, "mp") else 0.0
    mr = float(metrics.box.mr) if hasattr(metrics.box, "mr") else 0.0
    map50 = float(metrics.box.map50) if hasattr(metrics.box, "map50") else 0.0
    map50_95 = float(metrics.box.map) if hasattr(metrics.box, "map") else 0.0
    mean_f1 = float(2 * mp * mr / (mp + mr + 1e-16))

    # Per-class metrics
    per_class: Dict[str, Dict[str, float]] = {}
    p_per_class = metrics.box.p if hasattr(metrics.box, "p") else []
    r_per_class = metrics.box.r if hasattr(metrics.box, "r") else []
    ap50_per_class = metrics.box.ap50 if hasattr(metrics.box, "ap50") else []
    ap_per_class = metrics.box.ap if hasattr(metrics.box, "ap") else []

    for cid, cname in sorted(config.CLASS_NAMES.items()):
        p_c = float(p_per_class[cid]) if cid < len(p_per_class) else 0.0
        r_c = float(r_per_class[cid]) if cid < len(r_per_class) else 0.0
        f1_c = float(2 * p_c * r_c / (p_c + r_c + 1e-16))
        ap50_c = float(ap50_per_class[cid]) if cid < len(ap50_per_class) else 0.0
        ap_c = float(ap_per_class[cid]) if cid < len(ap_per_class) else 0.0
        per_class[cname] = {
            "class_id": cid,
            "precision": round(p_c, 4),
            "recall": round(r_c, 4),
            "f1": round(f1_c, 4),
            "ap50": round(ap50_c, 4),
            "ap50_95": round(ap_c, 4),
        }

    # Find optimal operating confidence threshold from F1 curve
    chosen_conf = 0.25  # Fallback standard
    f1_curve_data: List[float] = []

    if hasattr(metrics.box, "f1_curve") and metrics.box.f1_curve is not None:
        try:
            f1_curve = np.array(metrics.box.f1_curve)
            if f1_curve.ndim == 2:
                # Shape: (num_classes, 1000)
                mean_curve = f1_curve.mean(axis=0)
                best_idx = int(np.argmax(mean_curve))
                thresholds = np.linspace(0, 1, len(mean_curve))
                chosen_conf = float(thresholds[best_idx])
                f1_curve_data = [round(float(v), 4) for v in mean_curve]
            elif f1_curve.ndim == 1:
                best_idx = int(np.argmax(f1_curve))
                thresholds = np.linspace(0, 1, len(f1_curve))
                chosen_conf = float(thresholds[best_idx])
                f1_curve_data = [round(float(v), 4) for v in f1_curve]
        except Exception as e:
            print(f"[!] Note: F1 curve parsing used fallback: {e}")

    # Clamp chosen_conf to a sensible operational range [0.10, 0.85]
    chosen_conf = max(0.10, min(0.85, chosen_conf))

    summary = {
        "split": split,
        "overall": {
            "precision": round(mp, 4),
            "recall": round(mr, 4),
            "f1": round(mean_f1, 4),
            "map50": round(map50, 4),
            "map50_95": round(map50_95, 4),
        },
        "per_class": per_class,
        "chosen_threshold": round(chosen_conf, 4),
        "save_dir": str(metrics.save_dir) if hasattr(metrics, "save_dir") else "",
    }

    print("\n--- Validation Summary ---")
    print(f"  Precision       : {mp:.4f}")
    print(f"  Recall          : {mr:.4f}")
    print(f"  F1 Score        : {mean_f1:.4f}")
    print(f"  mAP@50          : {map50:.4f}")
    print(f"  mAP@50:95       : {map50_95:.4f}")
    print(f"  Optimal Conf Thresh : {chosen_conf:.4f} (chosen on VALIDATION split only)")
    return summary


def compute_iou(box1: np.ndarray, box2: np.ndarray) -> float:
    """Compute IoU between two bounding boxes [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


def evaluate_detections_on_image(
    gt_boxes: List[Tuple[int, np.ndarray]],  # list of (class_id, [x1, y1, x2, y2])
    pred_boxes: List[Tuple[int, float, np.ndarray]],  # list of (class_id, conf, [x1, y1, x2, y2])
    iou_thresh: float = 0.5,
) -> Dict[str, Any]:
    """Match predicted boxes to ground truth boxes using Greedy IoU matching."""
    matched_gt = set()
    tp_boxes = []
    fp_boxes = []

    # Sort predictions by confidence descending
    sorted_preds = sorted(pred_boxes, key=lambda x: x[1], reverse=True)

    for p_cls, p_conf, p_box in sorted_preds:
        best_iou = 0.0
        best_gt_idx = -1
        for g_idx, (g_cls, g_box) in enumerate(gt_boxes):
            if g_idx in matched_gt or g_cls != p_cls:
                continue
            iou = compute_iou(p_box, g_box)
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = g_idx

        if best_iou >= iou_thresh and best_gt_idx >= 0:
            matched_gt.add(best_gt_idx)
            tp_boxes.append((p_cls, p_conf, p_box, best_iou))
        else:
            fp_boxes.append((p_cls, p_conf, p_box, best_iou))

    fn_boxes = [gt_boxes[i] for i in range(len(gt_boxes)) if i not in matched_gt]

    return {
        "num_tp": len(tp_boxes),
        "num_fp": len(fp_boxes),
        "num_fn": len(fn_boxes),
        "tp_boxes": tp_boxes,
        "fp_boxes": fp_boxes,
        "fn_boxes": fn_boxes,
    }


def compute_bootstrap_confidence_intervals(
    image_eval_results: List[Dict[str, Any]],
    n_resamples: int = config.BOOTSTRAP_RESAMPLES,
    seed: int = config.BOOTSTRAP_SEED,
) -> Dict[str, Any]:
    """Compute non-parametric 95% bootstrap confidence intervals over test images."""
    rng = np.random.RandomState(seed)
    n_images = len(image_eval_results)

    b_precision: List[float] = []
    b_recall: List[float] = []
    b_f1: List[float] = []

    for _ in range(n_resamples):
        sample_indices = rng.randint(0, n_images, size=n_images)
        total_tp = sum(image_eval_results[i]["num_tp"] for i in sample_indices)
        total_fp = sum(image_eval_results[i]["num_fp"] for i in sample_indices)
        total_fn = sum(image_eval_results[i]["num_fn"] for i in sample_indices)

        p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

        b_precision.append(p)
        b_recall.append(r)
        b_f1.append(f1)

    ci_results = {
        "precision": {
            "mean": round(float(np.mean(b_precision)), 4),
            "ci_95": [round(float(np.percentile(b_precision, 2.5)), 4), round(float(np.percentile(b_precision, 97.5)), 4)],
        },
        "recall": {
            "mean": round(float(np.mean(b_recall)), 4),
            "ci_95": [round(float(np.percentile(b_recall, 2.5)), 4), round(float(np.percentile(b_recall, 97.5)), 4)],
        },
        "f1": {
            "mean": round(float(np.mean(b_f1)), 4),
            "ci_95": [round(float(np.percentile(b_f1, 2.5)), 4), round(float(np.percentile(b_f1, 97.5)), 4)],
        },
    }
    return ci_results


def run_near_duplicate_leakage_audit(
    train_img_dir: str,
    test_img_dir: str,
    image_eval_results: Optional[List[Dict[str, Any]]] = None,
    hamming_threshold: int = config.DHASH_HAMMING_THRESHOLD,
) -> Dict[str, Any]:
    """Audit near-duplicate leakage between train and test splits using 64-bit dHash and vectorized CPU LUT."""
    print("\n--- Running Near-Duplicate Leakage Audit (64-bit dHash) ---")
    train_files = sorted(Path(train_img_dir).glob("*.jpg"))
    test_files = sorted(Path(test_img_dir).glob("*.jpg"))

    print(f"Computing dHash for {len(train_files)} train images...")
    train_hashes = np.array([compute_dhash(str(p)) for p in train_files], dtype=np.int64)

    print(f"Computing dHash for {len(test_files)} test images...")
    test_hashes = np.array([compute_dhash(str(p)) for p in test_files], dtype=np.int64)

    # Vectorized CPU bit comparison
    min_distances = []
    has_duplicate_mask = []

    for t_hash in test_hashes:
        xor_vals = np.bitwise_xor(train_hashes, t_hash)
        bytes_view = xor_vals.view(np.uint8).reshape(-1, 8)
        counts = _BIT_COUNT_LUT[bytes_view].sum(axis=1)
        min_d = int(counts.min())
        min_distances.append(min_d)
        has_duplicate_mask.append(min_d <= hamming_threshold)

    near_dup_count = sum(has_duplicate_mask)
    dup_pct = (near_dup_count / len(test_files)) * 100 if test_files else 0.0

    report: Dict[str, Any] = {
        "train_image_count": len(train_files),
        "test_image_count": len(test_files),
        "hamming_distance_threshold": hamming_threshold,
        "test_images_with_near_duplicate": near_dup_count,
        "near_duplicate_percentage": round(dup_pct, 2),
        "min_hamming_distance_overall": int(min(min_distances)) if min_distances else -1,
    }

    # Evaluate metrics on duplicates vs non-duplicates if predictions are provided
    if image_eval_results is not None and len(image_eval_results) == len(test_files):
        for subset_name, mask_val in [("with_near_duplicate", True), ("without_near_duplicate", False)]:
            sub_indices = [i for i, val in enumerate(has_duplicate_mask) if val == mask_val]
            if not sub_indices:
                report[subset_name] = {"count": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
                continue

            sub_tp = sum(image_eval_results[i]["num_tp"] for i in sub_indices)
            sub_fp = sum(image_eval_results[i]["num_fp"] for i in sub_indices)
            sub_fn = sum(image_eval_results[i]["num_fn"] for i in sub_indices)

            p = sub_tp / (sub_tp + sub_fp) if (sub_tp + sub_fp) > 0 else 0.0
            r = sub_tp / (sub_tp + sub_fn) if (sub_tp + sub_fn) > 0 else 0.0
            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

            report[subset_name] = {
                "count": len(sub_indices),
                "precision": round(p, 4),
                "recall": round(r, 4),
                "f1": round(f1, 4),
            }

    print(f"[OK] Audit complete: {near_dup_count}/{len(test_files)} test images have near-duplicates ({dup_pct:.2f}%).")
    return report


def benchmark_speed_and_size(
    model_or_weights: Any,
    img_size: int = config.IMAGE_SIZE,
    device: Optional[str] = None,
    warmup_runs: int = config.SPEED_WARMUP_RUNS,
    timed_runs: int = config.SPEED_TIMED_RUNS,
    batch_size: int = config.SPEED_BATCH_SIZE,
) -> Dict[str, Any]:
    """Benchmark model checkpoint size, single-image GPU latency, and batch throughput."""
    import torch
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise ImportError("Ultralytics is required for speed benchmarking.") from e

    model_path_str = str(model_or_weights)
    file_size_mb = 0.0
    if os.path.exists(model_path_str):
        file_size_mb = round(os.path.getsize(model_path_str) / (1024 * 1024), 2)

    if isinstance(model_or_weights, str) or isinstance(model_or_weights, Path):
        model = YOLO(str(model_or_weights))
    else:
        model = model_or_weights

    target_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    is_cuda = target_device.startswith("cuda")

    # Single-image latency
    dummy_single = np.zeros((img_size, img_size, 3), dtype=np.uint8)

    # Warmup
    for _ in range(warmup_runs):
        _ = model.predict(source=dummy_single, verbose=False, device=target_device)
        if is_cuda:
            torch.cuda.synchronize()

    latencies_ms = []
    for _ in range(timed_runs):
        t0 = time.perf_counter()
        _ = model.predict(source=dummy_single, verbose=False, device=target_device)
        if is_cuda:
            torch.cuda.synchronize()
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    mean_lat = float(np.mean(latencies_ms))
    p50_lat = float(np.median(latencies_ms))
    p95_lat = float(np.percentile(latencies_ms, 95))
    p99_lat = float(np.percentile(latencies_ms, 99))

    # Batch throughput (batch_size images)
    batch_images = [dummy_single for _ in range(batch_size)]
    for _ in range(3):
        _ = model.predict(source=batch_images, verbose=False, device=target_device)
        if is_cuda:
            torch.cuda.synchronize()

    t_start = time.perf_counter()
    num_batches = 20
    for _ in range(num_batches):
        _ = model.predict(source=batch_images, verbose=False, device=target_device)
        if is_cuda:
            torch.cuda.synchronize()
    t_end = time.perf_counter()
    total_imgs = num_batches * batch_size
    fps = total_imgs / (t_end - t_start) if (t_end - t_start) > 0 else 0.0

    results = {
        "model_file_size_mb": file_size_mb,
        "device": target_device,
        "device_name": torch.cuda.get_device_name(0) if is_cuda else "CPU",
        "single_image_latency_ms": {
            "mean": round(mean_lat, 2),
            "p50": round(p50_lat, 2),
            "p95": round(p95_lat, 2),
            "p99": round(p99_lat, 2),
        },
        "batch_throughput_fps": round(fps, 2),
        "batch_size": batch_size,
    }

    print("\n--- Speed & SLA Benchmark ---")
    print(f"  Checkpoint Size : {file_size_mb} MB")
    print(f"  Single Image Latency (mean) : {mean_lat:.2f} ms ({p50_lat:.2f} ms p50, {p95_lat:.2f} ms p95)")
    print(f"  Batch {batch_size} Throughput     : {fps:.2f} images/sec")
    return results


def draw_boxes_on_image(
    img_bgr: np.ndarray,
    gt_boxes: List[Tuple[int, np.ndarray]],
    pred_boxes: List[Tuple[int, float, np.ndarray]],
) -> np.ndarray:
    """Render ground truth boxes in green and prediction boxes in red with labels."""
    canvas = img_bgr.copy()
    h, w = canvas.shape[:2]

    # Draw Ground Truth in Green
    for cls_id, box in gt_boxes:
        x1, y1, x2, y2 = [int(v) for v in box]
        cname = config.CLASS_MAPPING.get(cls_id, str(cls_id))
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            canvas,
            f"GT: {cname}",
            (x1, max(15, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

    # Draw Predictions in Magenta/Red
    for cls_id, conf, box in pred_boxes:
        x1, y1, x2, y2 = [int(v) for v in box]
        cname = config.CLASS_MAPPING.get(cls_id, str(cls_id))
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(
            canvas,
            f"{cname} {conf:.2f}",
            (x1, min(h - 5, y2 + 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )

    return canvas


def test_once(
    model_or_weights: Any,
    data_yaml: str,
    conf: float,
    output_dir: Optional[str] = None,
    force_rerun: bool = config.FORCE_RERUN,
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate YOLO model on the TEST split exactly once, protected by the safety guard.

    Refuses to run again if <output_dir>/test_metrics.json exists unless force_rerun=True.
    """
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise ImportError("Ultralytics is required for testing.") from e

    # Determine paths
    model_path = Path(str(model_or_weights))
    if output_dir is None:
        if model_path.is_file():
            # If weights are at <run_dir>/weights/best.pt, save evaluation at <run_dir>/evaluation
            eval_dir = model_path.parent.parent / "evaluation"
        else:
            eval_dir = Path("evaluation")
    else:
        eval_dir = Path(output_dir)

    metrics_path = eval_dir / "test_metrics.json"

    # Single-run guard
    if metrics_path.exists() and not force_rerun:
        print("=" * 70)
        print(f"[TEST GUARD ACTIVE] Test metrics already exist at: {metrics_path}")
        print("Refusing to re-run test evaluation to prevent test data snooping.")
        print("Set FORCE_RERUN=True only if you explicitly intend to overwrite test results.")
        print("=" * 70)
        with open(metrics_path, "r", encoding="utf-8") as f:
            return json.load(f)

    eval_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(model_or_weights, str) or isinstance(model_or_weights, Path):
        model = YOLO(str(model_or_weights))
    else:
        model = model_or_weights

    # Read dataset paths from data.yaml
    with open(data_yaml, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    data_root = ""
    for line in yaml_content.splitlines():
        if line.strip().startswith("path:"):
            data_root = line.split(":", 1)[1].strip()
            break

    if not data_root:
        raise ValueError(f"Could not parse 'path:' root from {data_yaml}")

    test_img_dir = Path(data_root) / "images" / "test"
    test_lbl_dir = Path(data_root) / "labels" / "test"
    train_img_dir = Path(data_root) / "images" / "train"

    test_images = sorted(list(test_img_dir.glob("*.jpg")))
    print("=" * 70)
    print(f"Running Protected Test Evaluation on {len(test_images)} images at conf={conf:.4f}...")
    print("=" * 70)

    # 1. Run Ultralytics test split validation for standardized mAP metrics
    val_kwargs = {
        "data": str(data_yaml),
        "split": "test",
        "conf": config.VAL_CONF,  # standard for mAP
        "iou": config.VAL_IOU,
        "batch": config.BATCH_SIZE,
        "plots": True,
        "workers": config.WORKERS,
    }
    if device is not None:
        val_kwargs["device"] = device

    test_val_res = model.val(**val_kwargs)
    mp = float(test_val_res.box.mp) if hasattr(test_val_res.box, "mp") else 0.0
    mr = float(test_val_res.box.mr) if hasattr(test_val_res.box, "mr") else 0.0
    map50 = float(test_val_res.box.map50) if hasattr(test_val_res.box, "map50") else 0.0
    map50_95 = float(test_val_res.box.map) if hasattr(test_val_res.box, "map") else 0.0

    # 2. Detailed Per-Image Evaluation at chosen operational conf
    image_eval_list = []
    country_stats: Dict[str, Dict[str, int]] = {
        c: {"tp": 0, "fp": 0, "fn": 0, "gt_damaged": 0, "pred_damaged": 0, "total_images": 0}
        for c in config.COUNTRIES
    }
    class_stats: Dict[str, Dict[str, int]] = {
        cname: {"tp": 0, "fp": 0, "fn": 0} for cname in config.CLASS_NAMES.values()
    }

    # Image-level confusion counts
    img_tp = 0
    img_fn = 0
    img_fp = 0
    img_tn = 0

    good_detections = []
    fn_detections = []
    fp_detections = []

    print(f"Running per-image inference on {len(test_images)} test images at operating conf={conf:.4f}...")
    for idx, img_path in enumerate(test_images):
        country = get_country_from_filename(img_path.name)
        stem = img_path.stem
        lbl_path = test_lbl_dir / f"{stem}.txt"

        # Read image to obtain dimensions
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            continue
        h, w = img_bgr.shape[:2]

        # Read ground truth
        gt_boxes = []
        if lbl_path.exists():
            with open(lbl_path, "r", encoding="utf-8") as lf:
                for line in lf:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        cid = int(parts[0])
                        xc, yc, bw, bh = [float(p) for p in parts[1:5]]
                        x1 = (xc - bw / 2.0) * w
                        y1 = (yc - bh / 2.0) * h
                        x2 = (xc + bw / 2.0) * w
                        y2 = (yc + bh / 2.0) * h
                        gt_boxes.append((cid, np.array([x1, y1, x2, y2])))

        # Run prediction
        preds = model.predict(source=str(img_path), conf=conf, iou=config.VAL_IOU, verbose=False, device=device)
        pred_boxes = []
        if len(preds) > 0 and preds[0].boxes is not None:
            for b in preds[0].boxes:
                cid = int(b.cls[0].item())
                c_conf = float(b.conf[0].item())
                xyxy = b.xyxy[0].cpu().numpy()
                pred_boxes.append((cid, c_conf, xyxy))

        # Match detections
        match_res = evaluate_detections_on_image(gt_boxes, pred_boxes, iou_thresh=0.5)
        num_tp = match_res["num_tp"]
        num_fp = match_res["num_fp"]
        num_fn = match_res["num_fn"]

        # Per-class counts
        for p_cls, _, _, _ in match_res["tp_boxes"]:
            cname = config.CLASS_NAMES.get(p_cls, str(p_cls))
            class_stats[cname]["tp"] += 1
        for p_cls, _, _, _ in match_res["fp_boxes"]:
            cname = config.CLASS_NAMES.get(p_cls, str(p_cls))
            class_stats[cname]["fp"] += 1
        for g_cls, _ in match_res["fn_boxes"]:
            cname = config.CLASS_NAMES.get(g_cls, str(g_cls))
            class_stats[cname]["fn"] += 1

        # Country counts
        if country in country_stats:
            country_stats[country]["tp"] += num_tp
            country_stats[country]["fp"] += num_fp
            country_stats[country]["fn"] += num_fn
            country_stats[country]["total_images"] += 1

        # Image-level evaluation:
        # "an image counts as damaged if it has any ground-truth box or any prediction above conf"
        gt_damaged = len(gt_boxes) > 0
        pred_damaged = len(pred_boxes) > 0

        if country in country_stats:
            if gt_damaged:
                country_stats[country]["gt_damaged"] += 1
            if pred_damaged:
                country_stats[country]["pred_damaged"] += 1

        if gt_damaged and pred_damaged:
            img_tp += 1
        elif gt_damaged and not pred_damaged:
            img_fn += 1
        elif not gt_damaged and pred_damaged:
            img_fp += 1
        else:
            img_tn += 1

        img_record = {
            "path": str(img_path),
            "filename": img_path.name,
            "country": country,
            "num_tp": num_tp,
            "num_fp": num_fp,
            "num_fn": num_fn,
            "gt_damaged": gt_damaged,
            "pred_damaged": pred_damaged,
        }
        image_eval_list.append(img_record)

        # Collect visualization candidates
        if len(good_detections) < config.VIS_NUM_GOOD and num_tp > 0 and num_fp == 0:
            good_detections.append((img_bgr, gt_boxes, pred_boxes, img_path.name, "good"))
        elif len(fn_detections) < config.VIS_NUM_FN and num_fn > 0:
            fn_detections.append((img_bgr, gt_boxes, pred_boxes, img_path.name, "false_negative"))
        elif len(fp_detections) < config.VIS_NUM_FP and num_fp > 0 and len(gt_boxes) == 0:
            fp_detections.append((img_bgr, gt_boxes, pred_boxes, img_path.name, "false_positive"))

    # Compute overall box-level metrics at operating conf
    total_tp = sum(r["num_tp"] for r in image_eval_list)
    total_fp = sum(r["num_fp"] for r in image_eval_list)
    total_fn = sum(r["num_fn"] for r in image_eval_list)
    op_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    op_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    op_f1 = 2 * op_precision * op_recall / (op_precision + op_recall + 1e-16)

    # Compute image-level FPR and FNR
    total_damaged_imgs = img_tp + img_fn
    total_clean_imgs = img_fp + img_tn
    image_fnr = img_fn / total_damaged_imgs if total_damaged_imgs > 0 else 0.0
    image_fpr = img_fp / total_clean_imgs if total_clean_imgs > 0 else 0.0
    image_accuracy = (img_tp + img_tn) / len(test_images) if test_images else 0.0

    # Per-country metrics table
    by_country_summary = {}
    for c, stats in sorted(country_stats.items()):
        c_tp, c_fp, c_fn = stats["tp"], stats["fp"], stats["fn"]
        cp = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
        cr = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
        cf1 = 2 * cp * cr / (cp + cr + 1e-16)
        by_country_summary[c] = {
            "total_images": stats["total_images"],
            "gt_damaged_images": stats["gt_damaged"],
            "pred_damaged_images": stats["pred_damaged"],
            "precision": round(cp, 4),
            "recall": round(cr, 4),
            "f1": round(cf1, 4),
            "tp_boxes": c_tp,
            "fp_boxes": c_fp,
            "fn_boxes": c_fn,
        }

    # Per-class metrics table
    by_class_summary = {}
    for cname, stats in sorted(class_stats.items()):
        c_tp, c_fp, c_fn = stats["tp"], stats["fp"], stats["fn"]
        cp = c_tp / (c_tp + c_fp) if (c_tp + c_fp) > 0 else 0.0
        cr = c_tp / (c_tp + c_fn) if (c_tp + c_fn) > 0 else 0.0
        cf1 = 2 * cp * cr / (cp + cr + 1e-16)
        by_class_summary[cname] = {
            "precision": round(cp, 4),
            "recall": round(cr, 4),
            "f1": round(cf1, 4),
            "tp_boxes": c_tp,
            "fp_boxes": c_fp,
            "fn_boxes": c_fn,
        }

    # Bootstrap 95% CIs
    ci_results = compute_bootstrap_confidence_intervals(
        image_eval_list,
        n_resamples=config.BOOTSTRAP_RESAMPLES,
        seed=config.BOOTSTRAP_SEED,
    )

    # Near-duplicate leakage check
    leakage_report = run_near_duplicate_leakage_audit(
        train_img_dir=str(train_img_dir),
        test_img_dir=str(test_img_dir),
        image_eval_results=image_eval_list,
        hamming_threshold=config.DHASH_HAMMING_THRESHOLD,
    )

    # Speed & size benchmark
    speed_report = benchmark_speed_and_size(
        model_or_weights=model_or_weights,
        img_size=config.IMAGE_SIZE,
        device=device,
        warmup_runs=config.SPEED_WARMUP_RUNS,
        timed_runs=config.SPEED_TIMED_RUNS,
        batch_size=config.SPEED_BATCH_SIZE,
    )

    # Assemble test_metrics.json
    test_metrics = {
        "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model_weights": str(model_or_weights),
        "chosen_confidence_threshold": round(conf, 4),
        "standard_mAP_metrics": {
            "mAP50": round(map50, 4),
            "mAP50_95": round(map50_95, 4),
            "mean_precision_at_001": round(mp, 4),
            "mean_recall_at_001": round(mr, 4),
        },
        "operating_box_metrics": {
            "precision": round(op_precision, 4),
            "recall": round(op_recall, 4),
            "f1": round(op_f1, 4),
            "total_tp_boxes": total_tp,
            "total_fp_boxes": total_fp,
            "total_fn_boxes": total_fn,
        },
        "image_level_metrics": {
            "total_images": len(test_images),
            "damaged_images": total_damaged_imgs,
            "clean_images": total_clean_imgs,
            "image_tp": img_tp,
            "image_fn": img_fn,
            "image_fp": img_fp,
            "image_tn": img_tn,
            "false_negative_rate_fnr": round(image_fnr, 4),
            "false_positive_rate_fpr": round(image_fpr, 4),
            "accuracy": round(image_accuracy, 4),
        },
        "bootstrap_95_ci": ci_results,
        "per_class_metrics": by_class_summary,
        "per_country_metrics": by_country_summary,
        "near_duplicate_leakage_audit": leakage_report,
        "speed_and_size_benchmark": speed_report,
    }

    # Save test_metrics.json
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(test_metrics, f, indent=2)
    print(f"\n[OK] Saved final test metrics to: {metrics_path}")

    # Copy curves and confusion matrix from Ultralytics val dir if available
    if hasattr(test_val_res, "save_dir") and test_val_res.save_dir:
        val_out = Path(test_val_res.save_dir)
        for fname in ["confusion_matrix.png", "BoxPR_curve.png", "BoxF1_curve.png", "BoxP_curve.png", "BoxR_curve.png"]:
            src = val_out / fname
            if src.exists():
                dst = eval_dir / fname.replace("Box", "").lower()
                shutil.copy2(src, dst)

    # Save 24 visual examples (8 good, 8 FN, 8 FP)
    vis_dir = eval_dir / "qualitative_examples"
    vis_dir.mkdir(parents=True, exist_ok=True)
    all_vis_examples = good_detections + fn_detections + fp_detections

    for img_bgr, gt_b, pred_b, fname, cat in all_vis_examples:
        annotated = draw_boxes_on_image(img_bgr, gt_b, pred_b)
        out_name = f"{cat}_{fname}"
        cv2.imwrite(str(vis_dir / out_name), annotated)

    print(f"[OK] Saved {len(all_vis_examples)} qualitative prediction crops to: {vis_dir}")
    return test_metrics

