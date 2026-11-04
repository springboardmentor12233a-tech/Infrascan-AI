"""
InfraScan Baseline Classifier Evaluation Module.
Evaluates trained ResNet-50 crack classifiers on the TEST split with:
- Strict validation reproducibility verification
- Test evaluation guard (single-run protection)
- Comprehensive test metrics (confusion matrix, ROC, PR curves)
- Bootstrap 95% confidence intervals (1,000 resamples)
- Surface group breakdown (for SDNET2018: Decks, Pavements, Walls)
- dHash leakage / near-duplicate Hamming distance audit
- GPU speed & model size benchmarking vs. SLA target

Functions only. Reuses build_model, CrackDataset, and load_manifest from train_classifier.py.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Import dependencies from training pipeline
try:
    from ml.classification.train_classifier import (
        build_model,
        CrackDataset,
        load_manifest,
        set_seed,
    )
    from ml.classification import config
except ImportError:
    try:
        from train_classifier import (
            build_model,
            CrackDataset,
            load_manifest,
            set_seed,
        )
        import config
    except ImportError:
        # Fallback path adjustment
        import sys
        _current_dir = Path(__file__).resolve().parent
        _infrascan_dir = _current_dir.parents[1]
        if str(_infrascan_dir) not in sys.path:
            sys.path.insert(0, str(_infrascan_dir))
        from ml.classification.train_classifier import (
            build_model,
            CrackDataset,
            load_manifest,
            set_seed,
        )
        from ml.classification import config

# Import shared preprocessing for throughput/latency benchmarks
try:
    from app.ai.preprocessing import preprocess, PreprocessConfig
except ImportError:
    import sys
    _infrascan_dir = Path(__file__).resolve().parents[2]
    _backend_dir = _infrascan_dir / "backend"
    if str(_backend_dir) not in sys.path:
        sys.path.insert(0, str(_backend_dir))
    try:
        from app.ai.preprocessing import preprocess, PreprocessConfig
    except ImportError:
        preprocess = None
        PreprocessConfig = None


# ==============================================================================
# 1. MODEL & CHECKPOINT LOADING
# ==============================================================================
def load_trained_model(
    model_dir: Union[str, Path],
    device: torch.device,
) -> Tuple[nn.Module, Dict[str, Any]]:
    """
    Load best checkpoint (best.pth) and associated model_card.json.
    Ensures model.eval() and leaves weights frozen for inference.
    """
    model_dir = Path(model_dir)
    best_pth = model_dir / "best.pth"
    model_card_path = model_dir / "model_card.json"

    if not best_pth.exists():
        raise FileNotFoundError(f"Trained checkpoint not found: {best_pth}")
    if not model_card_path.exists():
        raise FileNotFoundError(f"Model card not found: {model_card_path}")

    with open(model_card_path, "r", encoding="utf-8") as f:
        model_card = json.load(f)

    # Reconstruct architecture without downloading ImageNet weights
    model = build_model(pretrained=False)

    checkpoint = torch.load(best_pth, map_location=device)
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    elif isinstance(checkpoint, dict):
        model.load_state_dict(checkpoint)
    else:
        raise ValueError(f"Unexpected checkpoint format in {best_pth}")

    model.to(device)
    model.eval()

    print(f"[Model Loader] Loaded weights from {best_pth} (Device: {device})")
    print(f"[Model Loader] Chosen Threshold: {model_card.get('chosen_threshold', 0.5):.4f}")
    return model, model_card


# ==============================================================================
# 2. INFERENCE RUNNER
# ==============================================================================
@torch.no_grad()
def run_inference(
    model: nn.Module,
    dataset: CrackDataset,
    device: torch.device,
    batch_size: int = 64,
    num_workers: int = 2,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Execute forward pass over a dataset with torch.no_grad().
    Returns:
        all_targets: ground truth binary labels (N,)
        all_probs: predicted probabilities for crack class (N,)
    """
    model.eval()

    # Worker count guard for platforms without multiprocessing support
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers if os.name != "nt" else 0,
        pin_memory=torch.cuda.is_available(),
    )

    all_targets = []
    all_probs = []

    for images, targets in loader:
        images = images.to(device, non_blocking=True)
        logits = model(images).squeeze(-1)
        probs = torch.sigmoid(logits)

        all_targets.append(targets.cpu().numpy())
        all_probs.append(probs.cpu().numpy())

    all_targets = np.concatenate(all_targets).astype(int)
    all_probs = np.concatenate(all_probs).astype(float)
    return all_targets, all_probs


# ==============================================================================
# 3. REPRODUCIBILITY VERIFICATION (VALIDATION SPLIT)
# ==============================================================================
def verify_validation_reproducibility(
    model: nn.Module,
    val_df: pd.DataFrame,
    model_card: Dict[str, Any],
    device: torch.device,
    tolerance: float = 0.01,
) -> Dict[str, float]:
    """
    Run validation split inference and compare against logged validation metrics.
    STOPS with RuntimeError if F1 or Recall differs by > tolerance (0.01).
    """
    threshold = float(model_card.get("chosen_threshold", 0.5))
    use_clahe = bool(model_card.get("clahe_enabled", True))

    val_dataset = CrackDataset(val_df, is_train=False, use_clahe=use_clahe)
    val_targets, val_probs = run_inference(model, val_dataset, device=device)

    val_preds = (val_probs >= threshold).astype(int)
    reproduced_f1 = float(f1_score(val_targets, val_preds, zero_division=0))
    reproduced_recall = float(recall_score(val_targets, val_preds, zero_division=0))
    reproduced_prec = float(precision_score(val_targets, val_preds, zero_division=0))
    reproduced_acc = float(accuracy_score(val_targets, val_preds))

    logged_metrics = model_card.get("validation_metrics_at_threshold", {})
    logged_f1 = float(logged_metrics.get("f1_score", 0.0))
    logged_recall = float(logged_metrics.get("recall", 0.0))
    logged_prec = float(logged_metrics.get("precision", 0.0))
    logged_acc = float(logged_metrics.get("accuracy", 0.0))

    diff_f1 = abs(reproduced_f1 - logged_f1)
    diff_recall = abs(reproduced_recall - logged_recall)

    print("\n" + "=" * 60)
    print("VALIDATION REPRODUCIBILITY CHECK")
    print("=" * 60)
    print(f"{'Metric':<15} | {'Logged':<10} | {'Reproduced':<10} | {'Abs Diff':<10} | {'Status':<6}")
    print("-" * 60)
    print(f"{'F1 Score':<15} | {logged_f1:<10.4f} | {reproduced_f1:<10.4f} | {diff_f1:<10.4f} | {'PASS' if diff_f1 <= tolerance else 'FAIL'}")
    print(f"{'Recall':<15} | {logged_recall:<10.4f} | {reproduced_recall:<10.4f} | {diff_recall:<10.4f} | {'PASS' if diff_recall <= tolerance else 'FAIL'}")
    print(f"{'Precision':<15} | {logged_prec:<10.4f} | {reproduced_prec:<10.4f} | {abs(reproduced_prec - logged_prec):<10.4f} | -")
    print(f"{'Accuracy':<15} | {logged_acc:<10.4f} | {reproduced_acc:<10.4f} | {abs(reproduced_acc - logged_acc):<10.4f} | -")
    print("=" * 60)

    if diff_f1 > tolerance or diff_recall > tolerance:
        raise RuntimeError(
            f"Reproducibility verification FAILED! F1 diff={diff_f1:.4f} (tol={tolerance}), "
            f"Recall diff={diff_recall:.4f} (tol={tolerance}). Check model checkpoint or preprocessing."
        )

    print("[Reproducibility] Validation metrics reproduced successfully within tolerance.")
    return {
        "val_f1": reproduced_f1,
        "val_recall": reproduced_recall,
        "val_precision": reproduced_prec,
        "val_accuracy": reproduced_acc,
        "val_targets": val_targets,
        "val_probs": val_probs,
    }


# ==============================================================================
# 4. TEST RUN GUARD
# ==============================================================================
def check_test_guard(output_eval_dir: Path, force_rerun: bool = False) -> bool:
    """
    Guard single-use test split evaluation. Refuses to overwrite unless force_rerun=True.
    """
    test_metrics_path = output_eval_dir / "test_metrics.json"
    if test_metrics_path.exists() and not force_rerun:
        print("\n" + "!" * 70)
        print(f"[TEST GUARD WARNING] Evaluation already exists at: {test_metrics_path}")
        print("Refusing to re-run test evaluation to preserve test set integrity.")
        print("Set FORCE_RERUN=True to explicitly overwrite this evaluation.")
        print("!" * 70 + "\n")
        return False
    return True


# ==============================================================================
# 5. METRICS COMPUTATION (RULE a)
# ==============================================================================
def compute_comprehensive_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float,
) -> Dict[str, Any]:
    """
    Calculate all required test metrics under the chosen operating threshold.
    """
    y_pred = (y_prob >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    num_total = len(y_true)

    acc = float(accuracy_score(y_true, y_pred))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0

    try:
        auc_roc = float(roc_auc_score(y_true, y_prob))
    except ValueError:
        auc_roc = 0.0

    try:
        avg_prec = float(average_precision_score(y_true, y_prob))
    except ValueError:
        avg_prec = 0.0

    return {
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "specificity": round(spec, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "auc_roc": round(auc_roc, 4),
        "average_precision": round(avg_prec, 4),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "threshold_used": round(float(threshold), 4),
        "number_of_images": int(num_total),
    }


# ==============================================================================
# 6. VALIDATION THRESHOLD SWEEP (RULE e)
# ==============================================================================
def compute_validation_threshold_sweep(
    val_targets: np.ndarray,
    val_probs: np.ndarray,
    output_csv: Path,
) -> pd.DataFrame:
    """
    Sweep thresholds 0.01 to 0.99 strictly on the VALIDATION split.
    Saves threshold_sweep.csv.
    """
    records = []
    thresholds = np.linspace(0.01, 0.99, 99)

    for th in thresholds:
        th_val = round(float(th), 2)
        preds = (val_probs >= th_val).astype(int)
        p = float(precision_score(val_targets, preds, zero_division=0))
        r = float(recall_score(val_targets, preds, zero_division=0))
        f = float(f1_score(val_targets, preds, zero_division=0))
        records.append({"threshold": th_val, "precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4)})

    df_sweep = pd.DataFrame(records)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df_sweep.to_csv(output_csv, index=False)
    print(f"[Artifact] Saved validation threshold sweep: {output_csv}")
    return df_sweep


# ==============================================================================
# 7. BOOTSTRAP 95% CONFIDENCE INTERVALS (RULE f)
# ==============================================================================
def compute_bootstrap_confidence_intervals(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float,
    n_resamples: int = 1000,
    seed: int = 42,
) -> Dict[str, Dict[str, float]]:
    """
    1,000 bootstrap resamples on test split for recall, precision, F1, and AUC-ROC.
    Uses percentile method: [2.5%, 97.5%].
    """
    rng = np.random.default_rng(seed)
    n = len(y_true)

    recalls, precisions, f1s, aucs = [], [], [], []

    for _ in range(n_resamples):
        indices = rng.choice(n, size=n, replace=True)
        sample_true = y_true[indices]
        sample_prob = y_prob[indices]
        sample_pred = (sample_prob >= threshold).astype(int)

        recalls.append(recall_score(sample_true, sample_pred, zero_division=0))
        precisions.append(precision_score(sample_true, sample_pred, zero_division=0))
        f1s.append(f1_score(sample_true, sample_pred, zero_division=0))

        if len(np.unique(sample_true)) > 1:
            aucs.append(roc_auc_score(sample_true, sample_prob))

    def get_stats(arr: list) -> Dict[str, float]:
        np_arr = np.array(arr)
        low, high = np.percentile(np_arr, [2.5, 97.5])
        return {
            "mean": round(float(np.mean(np_arr)), 4),
            "ci_lower_95": round(float(low), 4),
            "ci_upper_95": round(float(high), 4),
        }

    ci_results = {
        "recall": get_stats(recalls),
        "precision": get_stats(precisions),
        "f1": get_stats(f1s),
        "auc_roc": get_stats(aucs) if len(aucs) > 0 else {"mean": 0.0, "ci_lower_95": 0.0, "ci_upper_95": 0.0},
    }

    print("[Bootstrap] Computed 95% Confidence Intervals (1,000 resamples):")
    for k, v in ci_results.items():
        print(f"  - {k:<10}: {v['mean']:.4f} [95% CI: {v['ci_lower_95']:.4f} - {v['ci_upper_95']:.4f}]")

    return ci_results


# ==============================================================================
# 8. VISUALIZATIONS (RULES c, d, g)
# ==============================================================================
def plot_side_by_side_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold: float,
    dataset_name: str,
    output_path: Path,
) -> None:
    """
    Generate side-by-side confusion matrix: counts and row-normalized (percentages).
    """
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    cm_norm = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis]
    cm_norm = np.nan_to_num(cm_norm)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    classes = ["No Crack (0)", "Crack (1)"]

    # Subplot 1: Counts
    im0 = axes[0].imshow(cm, interpolation="nearest", cmap="Blues")
    axes[0].set_title(f"Confusion Matrix (Counts)\nThreshold = {threshold:.2f}", fontsize=12)
    fig.colorbar(im0, ax=axes[0])
    axes[0].set_xticks([0, 1])
    axes[0].set_yticks([0, 1])
    axes[0].set_xticklabels(classes)
    axes[0].set_yticklabels(classes)
    axes[0].set_ylabel("True Label", fontsize=11)
    axes[0].set_xlabel("Predicted Label", fontsize=11)

    thresh_val = cm.max() / 2.0
    for i in range(2):
        for j in range(2):
            axes[0].text(
                j, i, f"{cm[i, j]:,}",
                ha="center", va="center",
                color="white" if cm[i, j] > thresh_val else "black",
                fontweight="bold", fontsize=12,
            )

    # Subplot 2: Row-normalized
    im1 = axes[1].imshow(cm_norm, interpolation="nearest", cmap="Greens", vmin=0, vmax=1.0)
    axes[1].set_title("Normalized Confusion Matrix (Row-Wise %)", fontsize=12)
    fig.colorbar(im1, ax=axes[1])
    axes[1].set_xticks([0, 1])
    axes[1].set_yticks([0, 1])
    axes[1].set_xticklabels(classes)
    axes[1].set_yticklabels(classes)
    axes[1].set_ylabel("True Label", fontsize=11)
    axes[1].set_xlabel("Predicted Label", fontsize=11)

    for i in range(2):
        for j in range(2):
            axes[1].text(
                j, i, f"{cm_norm[i, j] * 100:.1f}%",
                ha="center", va="center",
                color="white" if cm_norm[i, j] > 0.5 else "black",
                fontweight="bold", fontsize=12,
            )

    fig.suptitle(f"Test Split Performance: {dataset_name}", fontsize=14, y=1.03)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[Artifact] Saved confusion matrix plot: {output_path}")


def plot_roc_and_pr_curves(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float,
    dataset_name: str,
    roc_path: Path,
    pr_path: Path,
) -> None:
    """
    Generate ROC curve and PR curve with operating threshold marked.
    """
    # 1. ROC Curve
    fpr, tpr, roc_thresholds = roc_curve(y_true, y_prob)
    auc_val = roc_auc_score(y_true, y_prob)

    # Operating point
    y_pred = (y_prob >= threshold).astype(int)
    op_rec = recall_score(y_true, y_pred, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    op_fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    fig_roc, ax_roc = plt.subplots(figsize=(7, 6))
    ax_roc.plot(fpr, tpr, color="#1f77b4", lw=2, label=f"ROC Curve (AUC = {auc_val:.4f})")
    ax_roc.plot([0, 1], [0, 1], color="grey", lw=1.5, linestyle="--", label="Random Classifier")
    ax_roc.scatter([op_fpr], [op_rec], color="red", s=100, zorder=5,
                   label=f"Operating Point (Thresh={threshold:.2f})\nFPR={op_fpr:.3f}, Recall={op_rec:.3f}")

    ax_roc.set_xlim([0.0, 1.0])
    ax_roc.set_ylim([0.0, 1.05])
    ax_roc.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=11)
    ax_roc.set_ylabel("True Positive Rate (Recall)", fontsize=11)
    ax_roc.set_title(f"Receiver Operating Characteristic (ROC)\n{dataset_name}", fontsize=13)
    ax_roc.legend(loc="lower right", frameon=True)
    ax_roc.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    roc_path.parent.mkdir(parents=True, exist_ok=True)
    fig_roc.savefig(roc_path, dpi=150)
    plt.close(fig_roc)
    print(f"[Artifact] Saved ROC curve: {roc_path}")

    # 2. Precision-Recall Curve
    precisions, recalls, pr_thresholds = precision_recall_curve(y_true, y_prob)
    ap_val = average_precision_score(y_true, y_prob)
    op_prec = precision_score(y_true, y_pred, zero_division=0)

    fig_pr, ax_pr = plt.subplots(figsize=(7, 6))
    ax_pr.plot(recalls, precisions, color="#2ca02c", lw=2, label=f"PR Curve (AP = {ap_val:.4f})")
    ax_pr.scatter([op_rec], [op_prec], color="red", s=100, zorder=5,
                  label=f"Operating Point (Thresh={threshold:.2f})\nRecall={op_rec:.3f}, Prec={op_prec:.3f}")

    ax_pr.set_xlim([0.0, 1.0])
    ax_pr.set_ylim([0.0, 1.05])
    ax_pr.set_xlabel("Recall (Sensitivity)", fontsize=11)
    ax_pr.set_ylabel("Precision (PPV)", fontsize=11)
    ax_pr.set_title(f"Precision-Recall (PR) Curve\n{dataset_name}", fontsize=13)
    ax_pr.legend(loc="lower left", frameon=True)
    ax_pr.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    pr_path.parent.mkdir(parents=True, exist_ok=True)
    fig_pr.savefig(pr_path, dpi=150)
    plt.close(fig_pr)
    print(f"[Artifact] Saved PR curve: {pr_path}")


def plot_misclassified_examples(
    df: pd.DataFrame,
    y_true: np.ndarray,
    y_prob: np.ndarray,
    y_pred: np.ndarray,
    output_path: Path,
    n_examples: int = 16,
) -> None:
    """
    Display 16 most confident False Negatives and 16 most confident False Positives.
    FN: True crack (1), predicted no-crack (0), lowest probability of crack.
    FP: True no-crack (0), predicted crack (1), highest probability of crack.
    """
    df_eval = df.copy()
    df_eval["y_true"] = y_true
    df_eval["y_prob"] = y_prob
    df_eval["y_pred"] = y_pred

    # False Negatives (most confident: lowest p)
    fn_df = df_eval[(df_eval["y_true"] == 1) & (df_eval["y_pred"] == 0)].sort_values(by="y_prob", ascending=True)
    # False Positives (most confident: highest p)
    fp_df = df_eval[(df_eval["y_true"] == 0) & (df_eval["y_pred"] == 1)].sort_values(by="y_prob", ascending=False)

    top_fn = fn_df.head(n_examples)
    top_fp = fp_df.head(n_examples)

    fig, axes = plt.subplots(4, 8, figsize=(20, 11))
    fig.suptitle("Most Confident Misclassifications (Left: False Negatives | Right: False Positives)", fontsize=15, y=0.98)

    # Plot 16 False Negatives on columns 0-3
    for idx in range(n_examples):
        r, c = idx // 4, idx % 4
        ax = axes[r, c]
        if idx < len(top_fn):
            row = top_fn.iloc[idx]
            img_bgr = cv2.imread(str(row["path"]))
            if img_bgr is not None:
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                ax.imshow(img_rgb)
            ax.set_title(f"FN #{idx+1}: P(crack)={row['y_prob']:.3f}\nTrue: Crack (1)", fontsize=9, color="darkred")
        ax.axis("off")

    # Plot 16 False Positives on columns 4-7
    for idx in range(n_examples):
        r, c = idx // 4, 4 + (idx % 4)
        ax = axes[r, c]
        if idx < len(top_fp):
            row = top_fp.iloc[idx]
            img_bgr = cv2.imread(str(row["path"]))
            if img_bgr is not None:
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                ax.imshow(img_rgb)
            ax.set_title(f"FP #{idx+1}: P(crack)={row['y_prob']:.3f}\nTrue: No Crack (0)", fontsize=9, color="darkblue")
        ax.axis("off")

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[Artifact] Saved misclassified examples plot: {output_path}")


# ==============================================================================
# 9. SDNET2018 SURFACE GROUP BREAKDOWN (RULE h)
# ==============================================================================
def evaluate_sdnet_by_surface_group(
    test_df: pd.DataFrame,
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float,
    output_dir: Path,
) -> pd.DataFrame:
    """
    Compute metrics per surface group for SDNET2018:
    - D: Bridge Decks
    - P: Pavements
    - W: Walls
    Saves metrics_by_group.csv and group_metrics.png.
    """
    df = test_df.copy()
    df["y_true"] = y_true
    df["y_prob"] = y_prob
    df["y_pred"] = (y_prob >= threshold).astype(int)

    # Extract surface code (D, P, W)
    def extract_surface(p: str) -> str:
        norm = str(p).replace("\\", "/")
        parts = norm.split("/")
        for surface_code in ["D", "P", "W"]:
            if surface_code in parts:
                return surface_code
        return "Unknown"

    df["surface_group"] = df["path"].apply(extract_surface)
    surface_names = {
        "D": "Decks (Bridge Decks)",
        "P": "Pavements",
        "W": "Walls",
    }

    group_records = []
    for code, full_name in surface_names.items():
        sub = df[df["surface_group"] == code]
        if len(sub) == 0:
            continue

        yt = sub["y_true"].values
        yp = sub["y_pred"].values
        ypr = sub["y_prob"].values

        rec = float(recall_score(yt, yp, zero_division=0))
        prec = float(precision_score(yt, yp, zero_division=0))
        f1 = float(f1_score(yt, yp, zero_division=0))
        try:
            auc = float(roc_auc_score(yt, ypr))
        except ValueError:
            auc = 0.0

        tn, fp, fn, tp = confusion_matrix(yt, yp, labels=[0, 1]).ravel()
        spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

        group_records.append({
            "group_code": code,
            "surface_name": full_name,
            "total_images": len(sub),
            "crack_images": int((yt == 1).sum()),
            "no_crack_images": int((yt == 0).sum()),
            "recall": round(rec, 4),
            "precision": round(prec, 4),
            "f1": round(f1, 4),
            "auc_roc": round(auc, 4),
            "specificity": round(spec, 4),
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn),
        })

    df_groups = pd.DataFrame(group_records)
    csv_path = output_dir / "metrics_by_group.csv"
    df_groups.to_csv(csv_path, index=False)
    print(f"[Artifact] Saved SDNET2018 per-group metrics: {csv_path}")

    # Plot bar chart
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(df_groups))
    width = 0.2

    ax.bar(x - 1.5 * width, df_groups["recall"], width, label="Recall", color="#1f77b4")
    ax.bar(x - 0.5 * width, df_groups["precision"], width, label="Precision", color="#ff7f0e")
    ax.bar(x + 0.5 * width, df_groups["f1"], width, label="F1 Score", color="#2ca02c")
    ax.bar(x + 1.5 * width, df_groups["auc_roc"], width, label="AUC-ROC", color="#d62728")

    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['surface_name']}\n(N={r['total_images']:,})" for _, r in df_groups.iterrows()], fontsize=11)
    ax.set_ylabel("Metric Value", fontsize=11)
    ax.set_ylim([0.0, 1.1])
    ax.set_title("SDNET2018 Performance by Surface Group (Decks vs Pavements vs Walls)", fontsize=13)
    ax.legend(loc="lower right", frameon=True)
    ax.grid(True, linestyle=":", axis="y", alpha=0.6)

    # Label values on top of F1 bars
    for i, v in enumerate(df_groups["f1"]):
        ax.text(i + 0.5 * width, v + 0.02, f"{v:.2f}", ha="center", fontsize=9, fontweight="bold")

    plt.tight_layout()
    plot_path = output_dir / "group_metrics.png"
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    print(f"[Artifact] Saved SDNET2018 group comparison plot: {plot_path}")

    return df_groups


# ==============================================================================
# 10. LEAKAGE CHECK: 64-BIT DHASH & HAMMING DISTANCE (RULE i)
# ==============================================================================
def compute_image_dhash_64(img_path: Union[str, Path]) -> Optional[np.ndarray]:
    """
    Compute 64-bit difference hash (dHash) from 9x8 grayscale image.
    Returns 64-element boolean array, or None if unreadable.
    """
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    # 9 columns x 8 rows
    resized = cv2.resize(img, (9, 8), interpolation=cv2.INTER_AREA)
    # Compare adjacent pixels horizontally across 8 columns
    diff = resized[:, 1:] > resized[:, :-1]
    return diff.flatten()


def run_near_duplicate_leakage_audit(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    test_probs: np.ndarray,
    threshold: float,
    output_dir: Path,
    chunk_size: int = 500,
    device: Optional[torch.device] = None,
) -> Dict[str, Any]:
    """
    Compute 64-bit dHash for all train and test images.
    Find smallest Hamming distance from every test image to any train image.
    Report near duplicates (distance 0 to 2) and metric differences.
    """
    print(f"\n[Leakage Audit] Computing dHash for {len(train_df):,} train images...")
    train_hashes = []
    train_valid_idx = []
    for idx, path in enumerate(train_df["path"]):
        h = compute_image_dhash_64(path)
        if h is not None:
            train_hashes.append(h)
            train_valid_idx.append(idx)

    train_hashes = np.array(train_hashes, dtype=bool)

    print(f"[Leakage Audit] Computing dHash for {len(test_df):,} test images...")
    test_hashes = []
    test_valid_mask = []
    for idx, path in enumerate(test_df["path"]):
        h = compute_image_dhash_64(path)
        if h is not None:
            test_hashes.append(h)
            test_valid_mask.append(True)
        else:
            test_valid_mask.append(False)

    test_hashes = np.array(test_hashes, dtype=bool)
    n_test = len(test_hashes)
    min_hamming_dists = np.zeros(n_test, dtype=np.int32)

    # Vectorized chunked Hamming distance using NumPy on CPU (zero GPU VRAM usage)
    print(f"[Leakage Audit] Calculating nearest train neighbor distances using NumPy chunks...")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    lut = np.array([bin(b).count("1") for b in range(256)], dtype=np.uint8)
    train_bytes = np.packbits(train_hashes, axis=1)
    test_bytes = np.packbits(test_hashes, axis=1)

    for i in range(0, n_test, chunk_size):
        chunk = test_bytes[i:i + chunk_size]
        xor = np.bitwise_xor(chunk[:, None, :], train_bytes[None, :, :])
        dists = lut[xor].sum(axis=2)
        min_hamming_dists[i:i + chunk_size] = dists.min(axis=1)

    # Filter test dataframe for valid hashes
    df_leakage = test_df[test_valid_mask].copy().reset_index(drop=True)
    df_leakage["min_hamming_dist"] = min_hamming_dists
    df_leakage["has_near_duplicate"] = df_leakage["min_hamming_dist"] <= 2
    df_leakage["probability"] = test_probs[test_valid_mask]
    df_leakage["prediction"] = (df_leakage["probability"] >= threshold).astype(int)

    # Save detailed per-image report
    report_csv = output_dir / "near_duplicate_report.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    df_leakage.to_csv(report_csv, index=False)
    print(f"[Artifact] Saved near-duplicate leakage report: {report_csv}")

    # Compute breakdown counts
    d0_count = int((min_hamming_dists == 0).sum())
    d1_count = int((min_hamming_dists == 1).sum())
    d2_count = int((min_hamming_dists == 2).sum())
    near_dup_count = int((min_hamming_dists <= 2).sum())
    no_dup_count = int((min_hamming_dists > 2).sum())

    # Performance comparison: WITH near-duplicate vs WITHOUT
    def calc_split_metrics(sub_df: pd.DataFrame) -> Dict[str, float]:
        if len(sub_df) == 0:
            return {"recall": 0.0, "f1": 0.0, "precision": 0.0, "count": 0}
        yt = sub_df["label"].values
        yp = sub_df["prediction"].values
        return {
            "count": len(sub_df),
            "recall": round(float(recall_score(yt, yp, zero_division=0)), 4),
            "f1": round(float(f1_score(yt, yp, zero_division=0)), 4),
            "precision": round(float(precision_score(yt, yp, zero_division=0)), 4),
        }

    metrics_with_dup = calc_split_metrics(df_leakage[df_leakage["has_near_duplicate"]])
    metrics_without_dup = calc_split_metrics(df_leakage[~df_leakage["has_near_duplicate"]])

    summary = {
        "total_test_images_checked": n_test,
        "exact_duplicates_dist_0": d0_count,
        "near_duplicates_dist_1": d1_count,
        "near_duplicates_dist_2": d2_count,
        "total_near_duplicates_dist_0_to_2": near_dup_count,
        "percentage_near_duplicates": round(near_dup_count / max(n_test, 1) * 100, 2),
        "metrics_with_near_duplicate": metrics_with_dup,
        "metrics_without_near_duplicate": metrics_without_dup,
    }

    summary_json = output_dir / "near_duplicate_summary.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[Artifact] Saved near-duplicate summary: {summary_json}")

    print("\n" + "=" * 60)
    print("DATASET LEAKAGE AUDIT (dHash 64-bit)")
    print("=" * 60)
    print(f"Total Test Images Audited:          {n_test:,}")
    print(f"Distance 0 (Exact Duplicate):       {d0_count:,} ({d0_count / max(n_test, 1) * 100:.2f}%)")
    print(f"Distance 1:                         {d1_count:,}")
    print(f"Distance 2:                         {d2_count:,}")
    print(f"Total Near Duplicates (Dist 0-2):   {near_dup_count:,} ({summary['percentage_near_duplicates']}%)")
    print("-" * 60)
    print(f"WITH Near Duplicate (N={metrics_with_dup['count']:,}):")
    print(f"  - Recall: {metrics_with_dup['recall']:.4f} | F1: {metrics_with_dup['f1']:.4f}")
    print(f"WITHOUT Near Duplicate (N={metrics_without_dup['count']:,}):")
    print(f"  - Recall: {metrics_without_dup['recall']:.4f} | F1: {metrics_without_dup['f1']:.4f}")
    print("=" * 60)

    return summary


# ==============================================================================
# 11. SPEED, SIZE & THROUGHPUT BENCHMARK (RULE j)
# ==============================================================================
def benchmark_inference_speed_and_size(
    model: nn.Module,
    model_checkpoint_path: Path,
    device: torch.device,
    input_size: int = 224,
    use_clahe: bool = True,
    warmup_runs: int = 10,
    timed_runs: int = 200,
    batch_size_tp: int = 64,
) -> Dict[str, Any]:
    """
    Measure model size on disk, GPU latency per image (batch=1, mean of 200 runs),
    and throughput for batch=64, including preprocessing and excluding image loading.
    Compares against 3.0 second latency target.
    """
    model.eval()

    # 1. File size on disk
    file_size_bytes = os.path.getsize(model_checkpoint_path) if model_checkpoint_path.exists() else 0
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

    # 2. Setup dummy input image for preprocessing
    dummy_bgr = np.random.randint(0, 256, (input_size, input_size, 3), dtype=np.uint8)

    # Setup preprocessing config
    if PreprocessConfig is not None:
        prep_config = PreprocessConfig(
            model_input_size=input_size,
            normalize_mode="imagenet",
            enable_contrast=use_clahe,
            enable_denoise=False,
            enable_sharpen=False,
        )
    else:
        prep_config = None

    # Warmup runs
    for _ in range(warmup_runs):
        if preprocess is not None and prep_config is not None:
            res = preprocess(dummy_bgr, config=prep_config)
            inp = torch.from_numpy(res.model_input).permute(2, 0, 1).unsqueeze(0).to(device)
        else:
            inp = torch.randn(1, 3, input_size, input_size, device=device)
        with torch.no_grad():
            _ = model(inp)
    if device.type == "cuda":
        torch.cuda.synchronize()

    # Timed single-image inference (Batch 1, 200 runs)
    single_latencies = []
    for _ in range(timed_runs):
        t0 = time.perf_counter()
        if preprocess is not None and prep_config is not None:
            res = preprocess(dummy_bgr, config=prep_config)
            inp = torch.from_numpy(res.model_input).permute(2, 0, 1).unsqueeze(0).to(device)
        else:
            inp = torch.randn(1, 3, input_size, input_size, device=device)

        with torch.no_grad():
            _ = model(inp)

        if device.type == "cuda":
            torch.cuda.synchronize()
        t1 = time.perf_counter()
        single_latencies.append((t1 - t0) * 1000.0)  # milliseconds

    mean_latency_ms = round(float(np.mean(single_latencies)), 2)
    std_latency_ms = round(float(np.std(single_latencies)), 2)
    mean_latency_sec = mean_latency_ms / 1000.0

    # 3. Batch 64 throughput
    batch_inps = torch.randn(batch_size_tp, 3, input_size, input_size, device=device)
    for _ in range(5):  # warmup batch
        with torch.no_grad():
            _ = model(batch_inps)
    if device.type == "cuda":
        torch.cuda.synchronize()

    t_batch_start = time.perf_counter()
    n_batch_iters = 20
    for _ in range(n_batch_iters):
        with torch.no_grad():
            _ = model(batch_inps)
    if device.type == "cuda":
        torch.cuda.synchronize()
    t_batch_elapsed = time.perf_counter() - t_batch_start
    throughput_fps = round((batch_size_tp * n_batch_iters) / t_batch_elapsed, 2)

    target_met = mean_latency_sec < 3.0

    benchmark_results = {
        "model_file_size_mb": file_size_mb,
        "single_image_latency_ms": mean_latency_ms,
        "single_image_latency_std_ms": std_latency_ms,
        "single_image_latency_sec": round(mean_latency_sec, 4),
        "batch_64_throughput_images_per_sec": throughput_fps,
        "target_latency_sec": 3.0,
        "target_satisfied": target_met,
    }

    print("\n" + "=" * 60)
    print("SPEED & HARDWARE BENCHMARK")
    print("=" * 60)
    print(f"Model Checkpoint Size:       {file_size_mb} MB")
    print(f"Inference Latency (Batch 1): {mean_latency_ms} ms ± {std_latency_ms} ms ({mean_latency_sec:.3f} s)")
    print(f"Throughput (Batch 64):       {throughput_fps} images/sec")
    print(f"Target Latency (3.0s):       {'MET' if target_met else 'NOT MET'} ({mean_latency_sec:.3f}s < 3.0s)")
    print("=" * 60)

    return benchmark_results


# ==============================================================================
# 12. FULL DATASET EVALUATOR (ORCHESTRATOR)
# ==============================================================================
def evaluate_dataset_classifier(
    model_dir: Union[str, Path],
    manifest_csv: Union[str, Path],
    data_root: Union[str, Path],
    dataset_name: str,
    device: Optional[torch.device] = None,
    force_rerun: bool = False,
) -> Dict[str, Any]:
    """
    Complete end-to-end evaluation pipeline on the TEST split for a single dataset:
    1. Check test run guard
    2. Load trained model & model card
    3. Load dataset splits
    4. Run reproducibility check on validation split
    5. Run threshold sweep on validation split only
    6. Run inference on test split
    7. Compute comprehensive test metrics & save test_metrics.json
    8. Save test_predictions.csv
    9. Generate confusion matrix, ROC, PR curves, and misclassifications plots
    10. Compute bootstrap 95% confidence intervals
    11. Run surface group analysis (if SDNET2018)
    12. Run near-duplicate leakage audit (dHash 64-bit)
    13. Benchmark inference speed and model size
    """
    model_dir = Path(model_dir)
    eval_dir = model_dir / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 1. Guard check
    can_proceed = check_test_guard(eval_dir, force_rerun=force_rerun)
    if not can_proceed:
        with open(eval_dir / "test_metrics.json", "r", encoding="utf-8") as f:
            return json.load(f)

    set_seed(42)

    # 2. Load model & model card
    model, model_card = load_trained_model(model_dir, device=device)
    threshold = float(model_card.get("chosen_threshold", 0.5))
    use_clahe = bool(model_card.get("clahe_enabled", True))

    # 3. Load splits
    train_df, val_df, test_df = load_manifest(manifest_csv, data_root=data_root)

    # 4. Reproducibility check on validation split FIRST
    val_repro = verify_validation_reproducibility(
        model=model,
        val_df=val_df,
        model_card=model_card,
        device=device,
        tolerance=0.01,
    )

    # 5. Validation threshold sweep (VALIDATION SPLIT ONLY - NEVER TEST)
    sweep_csv = eval_dir / "threshold_sweep.csv"
    compute_validation_threshold_sweep(val_repro["val_targets"], val_repro["val_probs"], sweep_csv)

    # 6. Test Split Inference
    print(f"\n[Test Split] Running inference over {len(test_df):,} test images (Threshold={threshold:.4f})...")
    test_dataset = CrackDataset(test_df, is_train=False, use_clahe=use_clahe)
    test_targets, test_probs = run_inference(model, test_dataset, device=device)
    test_preds = (test_probs >= threshold).astype(int)

    # 7. Comprehensive metrics (Rule a)
    test_metrics = compute_comprehensive_metrics(test_targets, test_probs, threshold=threshold)

    # 8. Save test predictions CSV (Rule b)
    pred_df = pd.DataFrame({
        "path": test_df["path"],
        "label": test_targets,
        "probability": test_probs,
        "prediction": test_preds,
    })
    if "group" in test_df.columns:
        pred_df["group"] = test_df["group"]

    pred_csv = eval_dir / "test_predictions.csv"
    pred_df.to_csv(pred_csv, index=False)
    print(f"[Artifact] Saved test predictions CSV: {pred_csv}")

    # 9. Visualizations (Rules c, d, g)
    cm_plot_path = eval_dir / "confusion_matrix.png"
    plot_side_by_side_confusion_matrix(test_targets, test_preds, threshold, dataset_name, cm_plot_path)

    roc_plot_path = eval_dir / "roc_curve.png"
    pr_plot_path = eval_dir / "pr_curve.png"
    plot_roc_and_pr_curves(test_targets, test_probs, threshold, dataset_name, roc_plot_path, pr_plot_path)

    misc_plot_path = eval_dir / "misclassified_examples.png"
    plot_misclassified_examples(test_df, test_targets, test_probs, test_preds, misc_plot_path, n_examples=16)

    # 10. Bootstrap 95% Confidence Intervals (Rule f)
    ci_results = compute_bootstrap_confidence_intervals(test_targets, test_probs, threshold=threshold, n_resamples=1000, seed=42)
    test_metrics["confidence_intervals_95"] = ci_results

    # Save test_metrics.json (Rule a)
    metrics_json_path = eval_dir / "test_metrics.json"
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(test_metrics, f, indent=2)
    print(f"[Artifact] Saved test metrics JSON: {metrics_json_path}")

    # 11. SDNET2018 Group Breakdown (Rule h)
    if "sdnet" in dataset_name.lower():
        print("\n[SDNET2018 Analysis] Evaluating surface group performance (Decks, Pavements, Walls)...")
        evaluate_sdnet_by_surface_group(test_df, test_targets, test_probs, threshold, eval_dir)

    # 12. Leakage Check (Rule i)
    leakage_summary = run_near_duplicate_leakage_audit(
        train_df=train_df,
        test_df=test_df,
        test_probs=test_probs,
        threshold=threshold,
        output_dir=eval_dir,
        chunk_size=500,
        device=device,
    )
    test_metrics["leakage_audit"] = leakage_summary

    # 13. Speed and Size (Rule j)
    speed_results = benchmark_inference_speed_and_size(
        model=model,
        model_checkpoint_path=model_dir / "best.pth",
        device=device,
        input_size=config.MODEL_INPUT_SIZE,
        use_clahe=use_clahe,
    )
    test_metrics["speed_and_size_benchmark"] = speed_results

    # Overwrite test_metrics.json with complete details
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(test_metrics, f, indent=2)

    return test_metrics

