from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .metrics import segmentation_metrics


def validate_pairs(images: Path, masks: Path) -> list[tuple[Path, Path]]:
    if not images.is_dir() or not masks.is_dir():
        raise FileNotFoundError("Segmentation requires existing image and mask directories.")
    image_files = {path.stem: path for path in images.iterdir() if path.is_file()}
    mask_files = {path.stem: path for path in masks.iterdir() if path.is_file()}
    pairs = sorted((image_files[key], mask_files[key]) for key in image_files.keys() & mask_files.keys())
    if not pairs:
        raise ValueError(
            "No image/mask pairs were found. The included classification dataset has no pixel masks; "
            "supply an annotated segmentation dataset."
        )
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Milestone 2 U-Net segmenter.")
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--masks", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("ml/artifacts/segmentation"))
    parser.add_argument("--epochs", type=int, default=25)
    args = parser.parse_args()
    pairs = validate_pairs(args.images, args.masks)
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
    except ImportError as exc:
        raise RuntimeError(
            "U-Net training requires PyTorch. Install it with: "
            "python -m pip install -r ml\\requirements-ml-optional.txt"
        ) from exc
    class MaskDataset(Dataset):
        def __init__(self, examples: list[tuple[Path, Path]]) -> None:
            self.examples = examples

        def __len__(self) -> int:
            return len(self.examples)

        def __getitem__(self, index: int):
            image_path, mask_path = self.examples[index]
            image = Image.open(image_path).convert("L").resize((128, 128))
            mask = Image.open(mask_path).convert("L").resize((128, 128))
            image_tensor = torch.from_numpy(np.asarray(image, dtype="float32") / 255.0).unsqueeze(0)
            mask_tensor = torch.from_numpy((np.asarray(mask, dtype="float32") > 127).astype("float32")).unsqueeze(0)
            return image_tensor, mask_tensor

    class DoubleConv(nn.Module):
        def __init__(self, input_channels: int, output_channels: int) -> None:
            super().__init__()
            self.layers = nn.Sequential(
                nn.Conv2d(input_channels, output_channels, 3, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(output_channels, output_channels, 3, padding=1),
                nn.ReLU(inplace=True),
            )

        def forward(self, inputs):
            return self.layers(inputs)

    class UNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.down1 = DoubleConv(1, 16)
            self.down2 = DoubleConv(16, 32)
            self.pool = nn.MaxPool2d(2)
            self.up = nn.ConvTranspose2d(32, 16, 2, stride=2)
            self.out = nn.Conv2d(32, 1, 1)

        def forward(self, inputs):
            first = self.down1(inputs)
            second = self.down2(self.pool(first))
            expanded = self.up(second)
            return self.out(torch.cat((expanded, first), dim=1))

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    loader = DataLoader(MaskDataset(pairs), batch_size=min(8, len(pairs)), shuffle=True)
    model = UNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_function = nn.BCEWithLogitsLoss()
    history: list[dict[str, float]] = []
    model.train()
    for epoch in range(args.epochs):
        total_loss = 0.0
        for images, masks in loader:
            optimizer.zero_grad()
            loss = loss_function(model(images), masks)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item())
        history.append({"epoch": epoch + 1, "loss": total_loss / len(loader)})
    model.eval()
    with torch.no_grad():
        images, masks = next(iter(loader))
        predictions = torch.sigmoid(model(images)).numpy()
    metrics = segmentation_metrics(predictions, masks.numpy())
    torch.save(model.state_dict(), output_dir / "unet_baseline.pt")
    (output_dir / "evaluation.json").write_text(
        json.dumps({"task": "crack segmentation", "pairs": len(pairs), "history": history,
                    "metrics": metrics.__dict__}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"pairs": len(pairs), "metrics": metrics.__dict__}, indent=2))


if __name__ == "__main__":
    main()
