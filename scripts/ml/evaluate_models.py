"""Recompute a short evaluation summary from saved checkpoints.

Classification and segmentation metrics are measured again on a fresh
group-aware sample so the report is not only the number stored at training time.
YOLO metrics are read from the training report because a full mAP pass is slow.
If a weight file is missing, that model is reported as not evaluated.

    backend\\venv\\Scripts\\python scripts\\ml\\evaluate_models.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.datasets import list_deepcrack_pairs, load_binary_mask  # noqa: E402
from app.ml.metrics import binary_classification_metrics, dice_iou  # noqa: E402
from app.ml.paths import (  # noqa: E402
    CLASSIFIER_WEIGHTS,
    REPORTS_DIR,
    UNET_WEIGHTS,
    YOLO_WEIGHTS,
)
from app.ml.preprocess import preprocess_for_model, resize_pair  # noqa: E402

PATCH = 64
SEED = 7


def _eval_classifier(torch) -> dict:
    if not CLASSIFIER_WEIGHTS.is_file():
        return {"status": "not_evaluated", "reason": "weights missing"}
    from app.ml.nets import SmallCNN

    checkpoint = torch.load(CLASSIFIER_WEIGHTS, map_location="cpu", weights_only=False)
    model = SmallCNN()
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    pairs = list_deepcrack_pairs()
    groups = sorted({pair["group"] for pair in pairs})
    rng = random.Random(SEED)
    rng.shuffle(groups)
    val_groups = set(groups[: max(1, len(groups) // 5)])
    chosen = [pair for pair in pairs if pair["group"] in val_groups][:8]
    np_rng = np.random.default_rng(SEED)
    y_true = []
    y_pred = []
    with torch.no_grad():
        for pair in chosen:
            image = cv2.imread(str(pair["image_path"]), cv2.IMREAD_COLOR)
            mask = load_binary_mask(pair["mask_path"])
            height, width = mask.shape[:2]
            taken = {0: 0, 1: 0}
            attempts = 0
            while sum(taken.values()) < 4 and attempts < 40:
                attempts += 1
                y = int(np_rng.integers(0, height - PATCH + 1))
                x = int(np_rng.integers(0, width - PATCH + 1))
                crop_mask = mask[y : y + PATCH, x : x + PATCH]
                fraction = float((crop_mask > 0).mean())
                label = 1 if fraction >= 0.02 else 0
                if 0 < fraction < 0.02 or taken[label] >= 2:
                    continue
                crop = image[y : y + PATCH, x : x + PATCH]
                tensor = preprocess_for_model(crop, size=(PATCH, PATCH), keep_aspect=False)
                logits = model(torch.from_numpy(tensor).unsqueeze(0))
                y_true.append(label)
                y_pred.append(int(logits.argmax(dim=1)))
                taken[label] += 1
    metrics = binary_classification_metrics(np.array(y_true), np.array(y_pred))
    return {
        "status": "evaluated",
        "held_out_check": metrics,
        "training_report_metrics": checkpoint.get("metrics"),
        "images_sampled": len(chosen),
        "official": False,
        "note": (
            "held_out_check uses seed 7 and is a second look, not the official training validation split. "
            "Quote training_report_metrics. The seed-7 groups can overlap images the model already trained on."
        ),
    }


def _eval_unet(torch) -> dict:
    if not UNET_WEIGHTS.is_file():
        return {"status": "not_evaluated", "reason": "weights missing"}
    from app.ml.nets import UNet

    checkpoint = torch.load(UNET_WEIGHTS, map_location="cpu", weights_only=False)
    base = int(checkpoint.get("config", {}).get("base_channels", 8))
    model = UNet(base=base)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    pairs = list_deepcrack_pairs()
    groups = sorted({pair["group"] for pair in pairs})
    rng = random.Random(SEED)
    rng.shuffle(groups)
    val_groups = set(groups[: max(1, len(groups) // 5)])
    chosen = [pair for pair in pairs if pair["group"] in val_groups][:6]
    dices, ious = [], []
    with torch.no_grad():
        for pair in chosen:
            image = cv2.imread(str(pair["image_path"]), cv2.IMREAD_COLOR)
            mask = load_binary_mask(pair["mask_path"])
            image, mask = resize_pair(image, mask, (128, 128))
            tensor = preprocess_for_model(image, size=(128, 128), keep_aspect=False)
            logits = model(torch.from_numpy(tensor).unsqueeze(0))
            prediction = (torch.sigmoid(logits)[0, 0].numpy() >= 0.5)
            dice, iou = dice_iou(prediction, mask > 0)
            dices.append(dice)
            ious.append(iou)
    return {
        "status": "evaluated",
        "dice": round(float(np.mean(dices)), 4),
        "iou": round(float(np.mean(ious)), 4),
        "images": len(chosen),
        "official": False,
        "training_report_metrics": checkpoint.get("metrics"),
        "note": (
            "This Dice and IoU are a 6-image seed-7 sample. They are not the official validation score. "
            "Quote training_report_metrics from the training run."
        ),
    }


def main() -> None:
    summary = {"classifier": {}, "segmentation": {}, "detection": {}}
    try:
        import torch
    except ImportError:
        torch = None
    if torch is None:
        summary["classifier"] = {"status": "not_evaluated", "reason": "torch is not installed"}
        summary["segmentation"] = {"status": "not_evaluated", "reason": "torch is not installed"}
    else:
        summary["classifier"] = _eval_classifier(torch)
        summary["segmentation"] = _eval_unet(torch)

    yolo_report = REPORTS_DIR / "yolo_metrics.json"
    if yolo_report.is_file():
        summary["detection"] = json.loads(yolo_report.read_text(encoding="utf-8"))
        summary["detection"]["weights_present"] = YOLO_WEIGHTS.is_file()
    else:
        summary["detection"] = {
            "status": "not_evaluated",
            "reason": "No YOLO training report. The detector was not scored.",
            "weights_present": YOLO_WEIGHTS.is_file(),
        }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    destination = REPORTS_DIR / "evaluation_summary.json"
    destination.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
