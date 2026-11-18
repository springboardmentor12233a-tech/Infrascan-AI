
from pathlib import Path
import random

import numpy as np
import torch
import matplotlib.pyplot as plt
from PIL import Image
from sklearn.model_selection import train_test_split

from train_unet import UNet

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "segmentation_experiments"
MODEL_ROOT = ROOT / "backend" / "models"

IMAGE_SIZE = (256, 256)
DEVICE = torch.device("cpu")
SEED = 42


def load_image(image_path):
    image = Image.open(image_path).convert("RGB")
    image = image.resize(IMAGE_SIZE)

    array = np.asarray(image, dtype=np.float32) / 255.0

    tensor = torch.from_numpy(
        array.transpose(2, 0, 1).copy()
    ).unsqueeze(0)

    return array, tensor


def load_mask(mask_path):
    mask = Image.open(mask_path).convert("L")
    mask = mask.resize(
        IMAGE_SIZE, Image.Resampling.NEAREST
    )

    return (np.asarray(mask) > 127).astype(np.uint8)


def load_model(name):
    model = UNet().to(DEVICE)

    checkpoint = MODEL_ROOT / f"m3_unet_{name}.pth"

    model.load_state_dict(
        torch.load(checkpoint, map_location=DEVICE)
    )

    model.eval()
    return model


def predict(model, image_tensor):
    with torch.no_grad():
        probabilities = torch.sigmoid(model(image_tensor))

    return (
        probabilities.squeeze().cpu().numpy() >= 0.5
    ).astype(np.uint8)


def main():
    torch.manual_seed(SEED)
    random.seed(SEED)
    np.random.seed(SEED)

    image_dir = DATA_ROOT / "label2_only" / "images"
    mask_a_dir = DATA_ROOT / "label2_only" / "masks"
    mask_b_dir = DATA_ROOT / "label2_plus4" / "masks"

    ids = sorted(
        p.stem for p in image_dir.glob("*.png")
        if (mask_a_dir / p.name).exists()
        and (mask_b_dir / p.name).exists()
    )

    _, val_ids = train_test_split(
        ids, test_size=0.2, random_state=SEED
    )

    print("Validation images:", len(val_ids))

    model_a = load_model("label2_only")
    model_b = load_model("label2_plus4")

    sample_ids = val_ids[:8]

    fig, axes = plt.subplots(
        len(sample_ids), 5,
        figsize=(18, 4 * len(sample_ids))
    )

    for row, image_id in enumerate(sample_ids):
        image_path = image_dir / f"{image_id}.png"

        original, image_tensor = load_image(image_path)

        actual_a = load_mask(
            mask_a_dir / f"{image_id}.png"
        )

        actual_b = load_mask(
            mask_b_dir / f"{image_id}.png"
        )

        prediction_a = predict(model_a, image_tensor)
        prediction_b = predict(model_b, image_tensor)

        images = [
            (original, "Original image"),
            (actual_a, "Ground truth A"),
            (prediction_a, "Prediction A"),
            (actual_b, "Ground truth B"),
            (prediction_b, "Prediction B"),
        ]

        for col, (content, title) in enumerate(images):
            ax = axes[row, col]

            if row == 0:
                ax.set_title(title, fontsize=11)

            if col == 0:
                ax.imshow(content)
            else:
                ax.imshow(content, cmap="gray", vmin=0, vmax=1)

            ax.axis("off")

        print(f"Compared image: {image_id}")

    plt.tight_layout()

    output_path = MODEL_ROOT / "m3_unet_ab_visual_comparison.png"

    plt.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close()

    print("\nVisual comparison saved:")
    print(output_path)


if __name__ == "__main__":
    main()
