from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True)
class ImageQuality:
    path: str
    width: int
    height: int
    mode: str
    format: str | None
    brightness_mean: float
    contrast_std: float
    sharpness_score: float
    is_low_light: bool
    is_low_contrast: bool
    is_blurry: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_image(path: Path) -> ImageQuality:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("L")
        pixels = np.asarray(image, dtype=np.float32)
        edge_response = np.asarray(image.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
        return ImageQuality(
            path=str(path),
            width=source.width,
            height=source.height,
            mode=source.mode,
            format=source.format,
            brightness_mean=float(pixels.mean()),
            contrast_std=float(pixels.std()),
            sharpness_score=float(edge_response.var()),
            is_low_light=bool(pixels.mean() < 45),
            is_low_contrast=bool(pixels.std() < 20),
            is_blurry=bool(edge_response.var() < 18),
        )


def preprocess_image(path: Path, size: int = 64) -> np.ndarray:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("L").resize((size, size))
        pixels = np.asarray(image, dtype=np.float32) / 255.0
    return (pixels - pixels.mean()) / max(float(pixels.std()), 1e-6)
