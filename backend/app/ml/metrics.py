"""Metric helpers that do not depend on scikit-learn."""

from __future__ import annotations

from typing import Any

import numpy as np


def binary_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Crack is the positive class (1). Returns accuracy, precision, recall, F1, and the confusion matrix."""
    y_true = np.asarray(y_true).astype(int).ravel()
    y_pred = np.asarray(y_pred).astype(int).ravel()
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    total = max(1, tp + tn + fp + fn)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "accuracy": round((tp + tn) / total, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "support": int(y_true.size),
        "confusion_matrix": {
            "labels": ["non_crack", "crack"],
            "matrix": [[tn, fp], [fn, tp]],
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "tp": tp,
        },
    }


def dice_iou(prediction: np.ndarray, target: np.ndarray) -> tuple[float, float]:
    """Dice and IoU for one binary mask. Both-empty masks score 1.0."""
    pred = prediction.astype(bool)
    truth = target.astype(bool)
    if not pred.any() and not truth.any():
        return 1.0, 1.0
    intersection = int(np.logical_and(pred, truth).sum())
    pred_sum = int(pred.sum())
    truth_sum = int(truth.sum())
    union = int(np.logical_or(pred, truth).sum())
    dice = (2.0 * intersection) / (pred_sum + truth_sum) if (pred_sum + truth_sum) else 0.0
    iou = intersection / union if union else 0.0
    return float(dice), float(iou)
