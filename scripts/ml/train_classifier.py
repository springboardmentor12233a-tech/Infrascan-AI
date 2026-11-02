"""Train the small crack / non-crack CNN on DeepCrack patches.

The published DeepCrack train/test split is not used. Crops that share a source
id (for example 11289-1 and 11289-2) stay in the same split. Metrics are
patch-level because non-crack examples are background patches, not separate
photographs. SDNET2018 was not available.

Run from the repository root with the Python 3.12 virtual environment:

    backend\\venv\\Scripts\\python scripts\\ml\\train_classifier.py
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
from app.ml.metrics import binary_classification_metrics  # noqa: E402
from app.ml.paths import CLASSIFIER_WEIGHTS, REPORTS_DIR, ensure_model_dirs  # noqa: E402
from app.ml.preprocess import preprocess_for_model  # noqa: E402

PATCH = 64
SEED = 42
MAX_TRAIN_IMAGES = 48
MAX_VAL_IMAGES = 12
PATCHES_PER_CLASS = 6
EPOCHS = 8
BATCH = 32
LEARNING_RATE = 1e-3


def _split_pairs(pairs: list[dict]) -> tuple[list[dict], list[dict], dict]:
    groups = sorted({pair["group"] for pair in pairs})
    rng = random.Random(SEED)
    rng.shuffle(groups)
    val_count = max(1, int(round(0.2 * len(groups))))
    val_groups = set(groups[:val_count])
    train = [pair for pair in pairs if pair["group"] not in val_groups]
    val = [pair for pair in pairs if pair["group"] in val_groups]
    rng.shuffle(train)
    rng.shuffle(val)
    train = train[:MAX_TRAIN_IMAGES]
    val = val[:MAX_VAL_IMAGES]
    info = {
        "seed": SEED,
        "strategy": "group-aware by DeepCrack source id; published split not used",
        "train_images_used": len(train),
        "val_images_used": len(val),
        "train_groups": sorted({pair["group"] for pair in train}),
        "val_groups": sorted({pair["group"] for pair in val}),
        "group_overlap": sorted({pair["group"] for pair in train} & {pair["group"] for pair in val}),
    }
    return train, val, info


def _sample_patches(pairs: list[dict], rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    images: list[np.ndarray] = []
    labels: list[int] = []
    for pair in pairs:
        image = cv2.imread(str(pair["image_path"]), cv2.IMREAD_COLOR)
        mask = load_binary_mask(pair["mask_path"])
        if image is None:
            continue
        height, width = mask.shape[:2]
        if height < PATCH or width < PATCH:
            continue
        found = {0: 0, 1: 0}
        attempts = 0
        while (found[0] < PATCHES_PER_CLASS or found[1] < PATCHES_PER_CLASS) and attempts < 100:
            attempts += 1
            y = int(rng.integers(0, height - PATCH + 1))
            x = int(rng.integers(0, width - PATCH + 1))
            crop_mask = mask[y : y + PATCH, x : x + PATCH]
            fraction = float((crop_mask > 0).mean())
            label = 1 if fraction >= 0.02 else 0
            if fraction > 0 and label == 0:
                continue
            if found[label] >= PATCHES_PER_CLASS:
                continue
            crop = image[y : y + PATCH, x : x + PATCH]
            images.append(preprocess_for_model(crop, size=(PATCH, PATCH), keep_aspect=False))
            labels.append(label)
            found[label] += 1
    if not images:
        raise RuntimeError("No patches were sampled. Check that DeepCrack is extracted.")
    return np.stack(images).astype(np.float32), np.array(labels, dtype=np.int64)


def _run_epoch(model, optimizer, loss_fn, features, labels, train: bool, torch) -> tuple[float, np.ndarray]:
    model.train(train)
    order = np.arange(len(labels))
    if train:
        np.random.default_rng(None).shuffle(order)
    losses = []
    predictions = np.zeros(len(labels), dtype=np.int64)
    for start in range(0, len(order), BATCH):
        batch_index = order[start : start + BATCH]
        xb = torch.from_numpy(features[batch_index])
        yb = torch.from_numpy(labels[batch_index])
        if train:
            optimizer.zero_grad()
        logits = model(xb)
        loss = loss_fn(logits, yb)
        if train:
            loss.backward()
            optimizer.step()
        losses.append(float(loss.detach()))
        predictions[batch_index] = logits.argmax(dim=1).detach().numpy()
    return float(np.mean(losses)), predictions


def main() -> None:
    import torch
    import torch.nn as nn

    from app.ml.nets import SmallCNN

    pairs = list_deepcrack_pairs()
    if len(pairs) < 20:
        raise SystemExit(f"Need DeepCrack pairs on disk. Found {len(pairs)}.")
    train_pairs, val_pairs, split_info = _split_pairs(pairs)
    rng = np.random.default_rng(SEED)
    print(f"Sampling patches from {len(train_pairs)} train and {len(val_pairs)} val images...")
    x_train, y_train = _sample_patches(train_pairs, rng)
    x_val, y_val = _sample_patches(val_pairs, rng)
    print(f"Train patches {len(y_train)} crack-rate {y_train.mean():.2f}; val patches {len(y_val)}")

    torch.manual_seed(SEED)
    model = SmallCNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_fn = nn.CrossEntropyLoss()
    best_f1 = -1.0
    best_state = None
    history = []
    for epoch in range(1, EPOCHS + 1):
        train_loss, train_pred = _run_epoch(model, optimizer, loss_fn, x_train, y_train, True, torch)
        with torch.no_grad():
            val_loss, val_pred = _run_epoch(model, optimizer, loss_fn, x_val, y_val, False, torch)
        train_metrics = binary_classification_metrics(y_train, train_pred)
        val_metrics = binary_classification_metrics(y_val, val_pred)
        history.append({"epoch": epoch, "train_loss": round(train_loss, 4), "val_loss": round(val_loss, 4), "val": val_metrics})
        print(
            f"epoch {epoch}: train_loss {train_loss:.4f} val_loss {val_loss:.4f} "
            f"val_f1 {val_metrics['f1']:.4f} val_acc {val_metrics['accuracy']:.4f}"
        )
        if val_metrics["f1"] >= best_f1:
            best_f1 = val_metrics["f1"]
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    model.load_state_dict(best_state)
    with torch.no_grad():
        _, final_pred = _run_epoch(model, optimizer, loss_fn, x_val, y_val, False, torch)
    final_metrics = binary_classification_metrics(y_val, final_pred)
    ensure_model_dirs()
    config = {
        "patch_size": PATCH,
        "epochs": EPOCHS,
        "batch_size": BATCH,
        "learning_rate": LEARNING_RATE,
        "max_train_images": MAX_TRAIN_IMAGES,
        "max_val_images": MAX_VAL_IMAGES,
        "patches_per_class_per_image": PATCHES_PER_CLASS,
        "positive_rule": "patch crack fraction >= 0.02",
        "negative_rule": "patch crack fraction == 0",
        "optimizer": "Adam",
        "device": "cpu",
    }
    checkpoint = {
        "model_name": "SmallCNN",
        "dataset": "DeepCrack local image-mask pairs",
        "input_size": PATCH,
        "classes": ["non_crack", "crack"],
        "state_dict": model.state_dict(),
        "metrics": final_metrics,
        "config": config,
        "split": split_info,
    }
    torch.save(checkpoint, CLASSIFIER_WEIGHTS)
    report = {
        "model_name": "SmallCNN",
        "dataset": "DeepCrack",
        "weights": str(CLASSIFIER_WEIGHTS),
        "config": config,
        "split": split_info,
        "validation_metrics": final_metrics,
        "history": history,
        "limitations": [
            "Metrics are on held-out patches, not on full images.",
            "Non-crack patches are background regions inside crack photographs.",
            "Only a capped subset of DeepCrack was used so training finishes on CPU.",
            "SDNET2018 and METU crack/non-crack photos were not available.",
        ],
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "classifier_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(final_metrics, indent=2))
    print(f"Saved {CLASSIFIER_WEIGHTS}")


if __name__ == "__main__":
    main()
