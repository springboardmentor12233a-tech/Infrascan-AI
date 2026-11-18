
from pathlib import Path
import random
import json

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split

from train_unet import UNet

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "segmentation_experiments"
OUTPUT_ROOT = ROOT / "backend" / "models"

IMAGE_SIZE = (256, 256)
BATCH_SIZE = 4
EPOCHS = 20
SEED = 42
DEVICE = torch.device("cpu")


class CrackDataset(Dataset):
    def __init__(self, ids, image_dir, mask_dir, augment=False):
        self.ids = ids
        self.image_dir = image_dir
        self.mask_dir = mask_dir
        self.augment = augment

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, index):
        image_id = self.ids[index]

        image = Image.open(
            self.image_dir / f"{image_id}.png"
        ).convert("RGB").resize(IMAGE_SIZE)

        mask = Image.open(
            self.mask_dir / f"{image_id}.png"
        ).convert("L").resize(
            IMAGE_SIZE, Image.Resampling.NEAREST
        )

        image = np.asarray(image, dtype=np.float32) / 255.0
        mask = np.asarray(mask) > 127

        if self.augment:
            if random.random() > 0.5:
                image = np.fliplr(image)
                mask = np.fliplr(mask)

            if random.random() > 0.5:
                image = np.flipud(image)
                mask = np.flipud(mask)

            rotations = random.randint(0, 3)
            image = np.rot90(image, rotations)
            mask = np.rot90(mask, rotations)

        image = torch.from_numpy(
            image.transpose(2, 0, 1).copy()
        )

        mask = torch.from_numpy(
            mask.astype(np.float32)[None, ...].copy()
        )

        return image, mask


def dice_loss(logits, targets):
    probabilities = torch.sigmoid(logits)

    intersection = (probabilities * targets).sum(
        dim=(1, 2, 3)
    )

    denominator = (
        probabilities.sum(dim=(1, 2, 3))
        + targets.sum(dim=(1, 2, 3))
    )

    dice = (2 * intersection + 1e-7) / (
        denominator + 1e-7
    )

    return 1 - dice.mean()


def evaluate(model, loader):
    model.eval()

    intersection = 0
    predicted_pixels = 0
    actual_pixels = 0

    with torch.no_grad():
        for images, masks in loader:
            probabilities = torch.sigmoid(model(images))
            predictions = probabilities >= 0.5
            targets = masks >= 0.5

            intersection += (predictions & targets).sum().item()
            predicted_pixels += predictions.sum().item()
            actual_pixels += targets.sum().item()

    union = predicted_pixels + actual_pixels - intersection

    iou = intersection / (union + 1e-7)
    dice = (2 * intersection) / (
        predicted_pixels + actual_pixels + 1e-7
    )

    return iou, dice


def train_experiment(name):
    print(f"\n========== {name} ==========")

    image_dir = DATA_ROOT / name / "images"
    mask_dir = DATA_ROOT / name / "masks"

    ids = sorted(
        p.stem for p in image_dir.glob("*.png")
        if (mask_dir / p.name).exists()
    )

    train_ids, val_ids = train_test_split(
        ids,
        test_size=0.2,
        random_state=SEED
    )

    train_loader = DataLoader(
        CrackDataset(train_ids, image_dir, mask_dir, True),
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0
    )

    val_loader = DataLoader(
        CrackDataset(val_ids, image_dir, mask_dir, False),
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0
    )

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    random.seed(SEED)

    model = UNet().to(DEVICE)

    optimizer = torch.optim.Adam(
        model.parameters(), lr=0.0005
    )

    bce_loss = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor([20.0], device=DEVICE)
    )

    best_dice = -1.0
    best_iou = 0.0

    checkpoint = OUTPUT_ROOT / f"m3_unet_{name}.pth"

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0

        for images, masks in train_loader:
            optimizer.zero_grad()

            logits = model(images)

            loss = (
                bce_loss(logits, masks)
                + dice_loss(logits, masks)
            )

            loss.backward()
            optimizer.step()

            total_loss += loss.item() * images.size(0)

        iou, dice = evaluate(model, val_loader)

        average_loss = total_loss / len(train_ids)

        print(
            f"Epoch {epoch + 1}/{EPOCHS} | "
            f"Loss: {average_loss:.4f} | "
            f"IoU: {iou:.4f} | Dice: {dice:.4f}"
        )

        if dice > best_dice:
            best_dice = dice
            best_iou = iou

            torch.save(model.state_dict(), checkpoint)
            print("Best checkpoint saved.")

    result = {
        "dataset": name,
        "training_images": len(train_ids),
        "validation_images": len(val_ids),
        "best_validation_iou": round(best_iou, 4),
        "best_validation_dice": round(best_dice, 4),
        "checkpoint": str(checkpoint)
    }

    print("Experiment result:", result)
    return result


def main():
    results = []

    for name in ["label2_only", "label2_plus4"]:
        results.append(train_experiment(name))

    report = OUTPUT_ROOT / "m3_unet_experiment_results.json"

    with open(report, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print("\nAll experiments completed.")
    print("Results saved:", report)


if __name__ == "__main__":
    main()
