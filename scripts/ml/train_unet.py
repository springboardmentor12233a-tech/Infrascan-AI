"""Train a small U-Net on DeepCrack image-mask pairs.

Images and masks receive the same resize and the same horizontal flip.
The published split is not used, because the EDA found source-image leakage.
Validation Dice and IoU are computed on held-out source groups.

    backend\\venv\\Scripts\\python scripts\\ml\\train_unet.py
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
from app.ml.metrics import dice_iou  # noqa: E402
from app.ml.paths import REPORTS_DIR, UNET_WEIGHTS, ensure_model_dirs  # noqa: E402
from app.ml.preprocess import apply_same_flip, preprocess_for_model, resize_pair  # noqa: E402

SIZE = 128
SEED = 42
MAX_TRAIN = 36
MAX_VAL = 8
EPOCHS = 6
BATCH = 4
BASE = 8
LEARNING_RATE = 1e-3


def _split(pairs: list[dict]) -> tuple[list[dict], list[dict], dict]:
    groups = sorted({pair["group"] for pair in pairs})
    rng = random.Random(SEED)
    rng.shuffle(groups)
    val_groups = set(groups[: max(1, int(round(0.2 * len(groups))))])
    train = [pair for pair in pairs if pair["group"] not in val_groups]
    val = [pair for pair in pairs if pair["group"] in val_groups]
    rng.shuffle(train)
    rng.shuffle(val)
    train, val = train[:MAX_TRAIN], val[:MAX_VAL]
    return train, val, {
        "seed": SEED,
        "strategy": "group-aware by DeepCrack source id; published split not used",
        "train_images_used": len(train),
        "val_images_used": len(val),
        "train_groups": sorted({pair["group"] for pair in train}),
        "val_groups": sorted({pair["group"] for pair in val}),
        "group_overlap": sorted({pair["group"] for pair in train} & {pair["group"] for pair in val}),
    }


def _load_example(pair: dict, augment: bool, rng: random.Random):
    image = cv2.imread(str(pair["image_path"]), cv2.IMREAD_COLOR)
    mask = load_binary_mask(pair["mask_path"])
    if image is None:
        raise ValueError(pair["image_path"])
    if augment and rng.random() < 0.5:
        image, mask = apply_same_flip(image, mask, horizontal=True)
    image, mask = resize_pair(image, mask, (SIZE, SIZE))
    tensor = preprocess_for_model(image, size=(SIZE, SIZE), imagenet=True, keep_aspect=False)
    target = (mask > 0).astype(np.float32)[None, :, :]
    return tensor, target


def _dice_loss(logits, target, torch):
    probs = torch.sigmoid(logits)
    intersection = (probs * target).sum(dim=(1, 2, 3))
    denom = probs.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3))
    dice = (2 * intersection + 1) / (denom + 1)
    return 1 - dice.mean()


def _evaluate(model, pairs, torch) -> dict:
    dices = []
    ious = []
    model.eval()
    with torch.no_grad():
        for pair in pairs:
            features, target = _load_example(pair, augment=False, rng=random.Random(0))
            logits = model(torch.from_numpy(features).unsqueeze(0))
            prediction = (torch.sigmoid(logits)[0, 0].numpy() >= 0.5)
            dice, iou = dice_iou(prediction, target[0] > 0.5)
            dices.append(dice)
            ious.append(iou)
    return {
        "dice": round(float(np.mean(dices)), 4) if dices else None,
        "iou": round(float(np.mean(ious)), 4) if ious else None,
        "images": len(dices),
    }


def main() -> None:
    import torch
    import torch.nn.functional as F

    from app.ml.nets import UNet

    pairs = list_deepcrack_pairs()
    if len(pairs) < 16:
        raise SystemExit(f"Need DeepCrack pairs on disk. Found {len(pairs)}.")
    train_pairs, val_pairs, split_info = _split(pairs)
    print(f"U-Net train images {len(train_pairs)} val images {len(val_pairs)}")
    rng = random.Random(SEED)
    torch.manual_seed(SEED)
    model = UNet(base=BASE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    best_dice = -1.0
    best_state = None
    history = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = list(range(len(train_pairs)))
        rng.shuffle(order)
        losses = []
        for start in range(0, len(order), BATCH):
            batch_ids = order[start : start + BATCH]
            features = []
            targets = []
            for index in batch_ids:
                feature, target = _load_example(train_pairs[index], augment=True, rng=rng)
                features.append(feature)
                targets.append(target)
            xb = torch.from_numpy(np.stack(features))
            yb = torch.from_numpy(np.stack(targets))
            optimizer.zero_grad()
            logits = model(xb)
            loss = F.binary_cross_entropy_with_logits(logits, yb) + _dice_loss(logits, yb, torch)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
        val_metrics = _evaluate(model, val_pairs, torch)
        row = {"epoch": epoch, "train_loss": round(float(np.mean(losses)), 4), "val": val_metrics}
        history.append(row)
        print(f"epoch {epoch}: loss {row['train_loss']:.4f} dice {val_metrics['dice']} iou {val_metrics['iou']}")
        if val_metrics["dice"] is not None and val_metrics["dice"] >= best_dice:
            best_dice = val_metrics["dice"]
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    model.load_state_dict(best_state)
    final_metrics = _evaluate(model, val_pairs, torch)
    ensure_model_dirs()
    config = {
        "input_size": SIZE,
        "epochs": EPOCHS,
        "batch_size": BATCH,
        "base_channels": BASE,
        "learning_rate": LEARNING_RATE,
        "loss": "BCE + soft Dice",
        "threshold": 0.5,
        "augmentation": "horizontal flip applied to image and mask together",
        "resize": "image INTER_AREA, mask INTER_NEAREST, same output size",
        "device": "cpu",
        "max_train_images": MAX_TRAIN,
        "max_val_images": MAX_VAL,
    }
    torch.save(
        {
            "model_name": "UNet",
            "dataset": "DeepCrack local image-mask pairs",
            "input_size": SIZE,
            "state_dict": model.state_dict(),
            "metrics": final_metrics,
            "config": config,
            "split": split_info,
        },
        UNET_WEIGHTS,
    )
    report = {
        "model_name": "UNet",
        "dataset": "DeepCrack",
        "weights": str(UNET_WEIGHTS),
        "config": config,
        "split": split_info,
        "validation_metrics": final_metrics,
        "history": history,
        "limitations": [
            "CPU baseline with 8 base channels and a small image cap.",
            "Dice and IoU are on the resized 128x128 validation masks.",
            "Published DeepCrack split was avoided because of source-image leakage.",
            "Pixel geometry derived from this mask is not a millimetre measurement.",
        ],
    }
    (REPORTS_DIR / "unet_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(final_metrics, indent=2))
    print(f"Saved {UNET_WEIGHTS}")


if __name__ == "__main__":
    main()
