"""Expert Severity Benchmark Evaluation Script.

Evaluates AI model damage severity against expert civil engineer ground-truth ratings.
Reads a CSV with columns: image_id, expert_severity (and optional predicted_severity).

Reports:
- Accuracy & Macro F1
- Quadratic Weighted Kappa (QWK)
- Confusion Matrix (Expert vs AI)
- Under-graded proportion (dangerous direction: defect severity underestimated)
- Over-graded proportion (conservative safety margin)
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np

from app.database import SessionLocal
from app.models.severity import SeverityAssessment
from app.services.severity_service import SEVERITY_ORDER, SEVERITY_RANK


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


def compute_macro_f1(y_true: List[int], y_pred: List[int], num_classes: int = 5) -> float:
    """Calculate unweighted macro F1 across severity categories."""
    f1_list = []
    for cls_idx in range(num_classes):
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls_idx and p == cls_idx)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls_idx and p == cls_idx)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls_idx and p != cls_idx)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        # Only average classes that exist in ground truth or predictions
        if (tp + fn) > 0 or (tp + fp) > 0:
            f1_list.append(f1)

    return float(np.mean(f1_list)) if f1_list else 0.0


def evaluate_expert_csv(csv_path: Path):
    if not csv_path.is_file():
        # Create a helpful template
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["image_id", "expert_severity"])
            writer.writerow([1, "minor"])
            writer.writerow([2, "moderate"])
        print(f"Created template expert severity CSV at: {csv_path}")
        print("Please populate with your expert ratings and rerun this script.")
        return

    # Read rows
    entries = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(row)

    if not entries:
        print(f"Error: {csv_path} contains no data rows.")
        return

    db = SessionLocal()

    true_ranks: List[int] = []
    pred_ranks: List[int] = []
    unmatched = 0

    try:
        for row in entries:
            img_id_str = row.get("image_id", "").strip()
            exp_sev = row.get("expert_severity", "").strip().lower()

            if exp_sev not in SEVERITY_RANK:
                print(f"Warning: skipping row with unknown expert_severity '{exp_sev}' for image {img_id_str}")
                continue

            # Check if predicted_severity is already in CSV
            pred_sev = row.get("predicted_severity", "").strip().lower()

            if not pred_sev or pred_sev not in SEVERITY_RANK:
                # Query DB for this image's assessment
                try:
                    img_id = int(img_id_str)
                    assessment = (
                        db.query(SeverityAssessment)
                        .filter(
                            SeverityAssessment.image_id == img_id,
                            SeverityAssessment.is_superseded == False,
                        )
                        .order_by(SeverityAssessment.assessment_id.desc())
                        .first()
                    )
                    if assessment:
                        pred_sev = assessment.final_severity or assessment.severity_level
                    else:
                        unmatched += 1
                        continue
                except Exception:
                    unmatched += 1
                    continue

            true_ranks.append(SEVERITY_RANK[exp_sev])
            pred_ranks.append(SEVERITY_RANK[pred_sev])

    finally:
        db.close()

    total = len(true_ranks)
    if total == 0:
        print("No matched images between CSV and database assessments.")
        return

    # Metrics
    matches = sum(1 for t, p in zip(true_ranks, pred_ranks) if t == p)
    acc = matches / total * 100.0

    macro_f1 = compute_macro_f1(true_ranks, pred_ranks, len(SEVERITY_ORDER))
    qwk = quadratic_weighted_kappa(true_ranks, pred_ranks, len(SEVERITY_ORDER))

    under_graded = sum(1 for t, p in zip(true_ranks, pred_ranks) if p < t)
    over_graded = sum(1 for t, p in zip(true_ranks, pred_ranks) if p > t)

    under_pct = (under_graded / total * 100.0)
    over_pct = (over_graded / total * 100.0)

    # Confusion Matrix
    conf_mat = np.zeros((len(SEVERITY_ORDER), len(SEVERITY_ORDER)), dtype=int)
    for t, p in zip(true_ranks, pred_ranks):
        conf_mat[t, p] += 1

    print("=" * 70)
    print("  EXPERT CIVIL ENGINEER SEVERITY BENCHMARK REPORT")
    print("=" * 70)
    print(f"Total Evaluated Pairs:         {total} (unmatched/skipped: {unmatched})")
    print(f"Exact Accuracy:                {matches}/{total} ({acc:.2f}%)")
    print(f"Macro F1 Score:                {macro_f1:.4f}")
    print(f"Quadratic Weighted Kappa:      {qwk:.4f}")
    print("-" * 70)
    print(f"Under-Graded Rate [DANGEROUS]: {under_graded}/{total} ({under_pct:.2f}%)  <-- Defect severity underestimated")
    print(f"Over-Graded Rate [CONSERVATIVE]: {over_graded}/{total} ({over_pct:.2f}%) <-- Conservative safety flag")
    print("-" * 70)
    print("\nConfusion Matrix (Rows: Expert Standard, Columns: AI Output):")
    hdr = f"{'Expert Standard':<15} | " + " | ".join(f"{lvl:>8}" for lvl in SEVERITY_ORDER)
    print(hdr)
    print("-" * len(hdr))
    for i, row_lvl in enumerate(SEVERITY_ORDER):
        row_str = f"{row_lvl:<15} | " + " | ".join(f"{conf_mat[i, j]:>8}" for j in range(len(SEVERITY_ORDER)))
        print(row_str)
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Expert Severity Benchmark Evaluation")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(r"D:\Infosys springboards\data\expert_severity.csv"),
        help="Path to CSV with columns (image_id, expert_severity)",
    )
    args = parser.parse_args()
    evaluate_expert_csv(args.csv)

