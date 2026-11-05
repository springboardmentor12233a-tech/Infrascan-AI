"""
Shared image preprocessing pipeline for InfraScan.

Designed as a standalone module without dependencies on FastAPI or the database,
so it can be directly imported in model training scripts, evaluation pipelines,
and Jupyter notebooks.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

# Reuse sharpness and brightness assessment functions from quality.py (no duplication)
from app.ai.quality import calculate_blur_score, calculate_brightness_score


@dataclass
class PreprocessConfig:
    """Configuration switches and parameters for the preprocessing pipeline."""
    model_input_size: int = 256
    normalize_mode: str = "zero_one"  # "zero_one" or "imagenet"
    enable_contrast: bool = True
    enable_denoise: bool = False
    enable_sharpen: bool = False
    clahe_clip_limit: float = 2.0
    clahe_tile_grid: int = 8

    @classmethod
    def from_env_or_defaults(cls) -> "PreprocessConfig":
        """Instantiate config reading environment variables when present, otherwise fallback to defaults."""
        return cls(
            model_input_size=int(os.getenv("MODEL_INPUT_SIZE", "256")),
            normalize_mode=os.getenv("NORMALIZE_MODE", "zero_one").lower(),
            enable_contrast=os.getenv("ENABLE_CONTRAST", "true").lower() in ("true", "1", "yes"),
            enable_denoise=os.getenv("ENABLE_DENOISE", "false").lower() in ("true", "1", "yes"),
            enable_sharpen=os.getenv("ENABLE_SHARPEN", "false").lower() in ("true", "1", "yes"),
            clahe_clip_limit=float(os.getenv("CLAHE_CLIP_LIMIT", "2.0")),
            clahe_tile_grid=int(os.getenv("CLAHE_TILE_GRID", "8")),
        )


@dataclass
class PreprocessResult:
    """Output artifacts and metadata produced by the preprocessing pipeline."""
    enhanced_image: np.ndarray  # Full-resolution enhanced image in BGR (uint8)
    model_input: np.ndarray     # Resized, padded, normalized float32 array (H, W, 3)
    steps_applied: List[str]    # Ordered list of processing steps applied
    original_size: Tuple[int, int]  # (height, width)
    model_size: Tuple[int, int]     # (height, width)
    pad_info: Dict[str, Any] = field(default_factory=dict)  # Padding information for mapping masks back


def preprocess(
    image_bgr: np.ndarray,
    config: Optional[Union[PreprocessConfig, Dict[str, Any]]] = None,
) -> PreprocessResult:
    """
    Execute initial image preprocessing on an input BGR numpy array.

    Steps applied:
    1. Contrast enhancement via CLAHE on the L channel of LAB color space (if enabled).
    2. Optional light noise reduction (if enabled).
    3. Optional mild unsharp mask sharpening (if enabled).
    4. BGR to RGB color conversion (for model input).
    5. Letterbox aspect-ratio preserving resize to model_input_size with black padding.
    6. Normalization ("zero_one" or "imagenet") yielding float32 array.

    Note: YOLO does its own resize and scaling, so for YOLO use enhanced_image directly.
    """
    if not isinstance(image_bgr, np.ndarray):
        raise TypeError(f"Expected numpy.ndarray for image_bgr, got {type(image_bgr)}")

    # Parse configuration
    if config is None:
        cfg = PreprocessConfig.from_env_or_defaults()
    elif isinstance(config, dict):
        cfg = PreprocessConfig(
            model_input_size=config.get("model_input_size", 256),
            normalize_mode=config.get("normalize_mode", "zero_one").lower(),
            enable_contrast=config.get("enable_contrast", True),
            enable_denoise=config.get("enable_denoise", False),
            enable_sharpen=config.get("enable_sharpen", False),
            clahe_clip_limit=float(config.get("clahe_clip_limit", 2.0)),
            clahe_tile_grid=int(config.get("clahe_tile_grid", 8)),
        )
    else:
        cfg = config

    orig_h, orig_w = image_bgr.shape[:2]
    steps_applied: List[str] = []

    # Start with a copy of the input image for full-resolution enhancement
    enhanced = image_bgr.copy()

    # --- Step 2: Full-Resolution Enhancement ---
    # 2a. Contrast enhancement: CLAHE on L channel in LAB color space
    if cfg.enable_contrast:
        lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(
            clipLimit=cfg.clahe_clip_limit,
            tileGridSize=(cfg.clahe_tile_grid, cfg.clahe_tile_grid),
        )
        l_clahe = clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge((l_clahe, a, b)), cv2.COLOR_LAB2BGR)
        steps_applied.append("contrast_clahe")

    # 2b. Denoise: Edge-preserving light noise reduction
    if cfg.enable_denoise:
        # Bilateral filter preserves crack edges while smoothing high-frequency noise
        enhanced = cv2.bilateralFilter(enhanced, d=5, sigmaColor=25, sigmaSpace=25)
        steps_applied.append("denoise")

    # 2c. Sharpen: Mild unsharp mask
    if cfg.enable_sharpen:
        # Subtract low frequencies and blend back with controlled factor
        blurred = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=2.0)
        enhanced = cv2.addWeighted(enhanced, 1.25, blurred, -0.25, 0)
        steps_applied.append("sharpen")

    # Note: YOLO does its own resize and scaling, so for YOLO use enhanced_image directly.

    # --- Step 1: Color Conversion for Model Input ---
    # Convert BGR to RGB for model_input only (enhanced_image remains BGR for OpenCV saving)
    model_rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
    steps_applied.append("bgr_to_rgb")

    # --- Step 3: Letterbox Resize & Padding ---
    target_size = cfg.model_input_size
    target_h, target_w = target_size, target_size

    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = int(round(orig_w * scale))
    new_h = int(round(orig_h * scale))

    resized = cv2.resize(model_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    pad_w = target_w - new_w
    pad_h = target_h - new_h
    pad_top = pad_h // 2
    pad_bottom = pad_h - pad_top
    pad_left = pad_w // 2
    pad_right = pad_w - pad_left

    # Pad with black [0, 0, 0] to preserve aspect ratio
    padded = cv2.copyMakeBorder(
        resized,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        cv2.BORDER_CONSTANT,
        value=[0, 0, 0],
    )
    steps_applied.append("letterbox_resize")

    pad_info = {
        "scale": scale,
        "new_w": new_w,
        "new_h": new_h,
        "pad_top": pad_top,
        "pad_bottom": pad_bottom,
        "pad_left": pad_left,
        "pad_right": pad_right,
        "target_w": target_w,
        "target_h": target_h,
    }

    # --- Step 4: Normalization ---
    model_float = padded.astype(np.float32)

    if cfg.normalize_mode == "imagenet":
        # Divide by 255.0 then apply standard ImageNet mean and std
        model_float = model_float / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        model_input = (model_float - mean) / std
        steps_applied.append("normalize_imagenet")
    else:
        # Default "zero_one" mode: scale values to [0.0, 1.0]
        model_input = model_float / 255.0
        steps_applied.append("normalize_zero_one")

    return PreprocessResult(
        enhanced_image=enhanced,
        model_input=model_input,
        steps_applied=steps_applied,
        original_size=(orig_h, orig_w),
        model_size=(target_h, target_w),
        pad_info=pad_info,
    )


def to_tiles(
    image: np.ndarray,
    tile_size: int = 256,
    overlap: int = 0,
) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
    """
    Slice an image into square tiles with a specified pixel overlap.

    Returns a list of tuples: (tile_array, (y1, x1, y2, x2))
    where (y1, x1, y2, x2) are the bounding coordinates within the source image.
    Ensures complete coverage of boundaries without truncation.
    """
    if tile_size <= 0:
        raise ValueError("tile_size must be positive")
    if overlap < 0 or overlap >= tile_size:
        raise ValueError("overlap must be >= 0 and < tile_size")

    stride = tile_size - overlap
    h, w = image.shape[:2]
    tiles: List[Tuple[np.ndarray, Tuple[int, int, int, int]]] = []

    # Handle image smaller than tile_size
    if h < tile_size or w < tile_size:
        pad_bottom = max(0, tile_size - h)
        pad_right = max(0, tile_size - w)
        padded = cv2.copyMakeBorder(
            image, 0, pad_bottom, 0, pad_right, cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )
        return [(padded[:tile_size, :tile_size], (0, 0, min(h, tile_size), min(w, tile_size)))]

    y = 0
    while y < h:
        y1 = y
        y2 = min(y1 + tile_size, h)
        if y2 - y1 < tile_size:
            y1 = max(0, h - tile_size)
            y2 = h

        x = 0
        while x < w:
            x1 = x
            x2 = min(x1 + tile_size, w)
            if x2 - x1 < tile_size:
                x1 = max(0, w - tile_size)
                x2 = w

            tile = image[y1:y2, x1:x2]
            tiles.append((tile, (y1, x1, y2, x2)))

            if x2 >= w:
                break
            x += stride

        if y2 >= h:
            break
        y += stride

    return tiles


def save_enhanced(path: Union[str, Path], image: np.ndarray) -> bool:
    """
    Save enhanced image to disk as a high-quality JPEG (quality 95).
    Creates parent directories automatically if they do not exist.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return bool(cv2.imwrite(str(target), image, [int(cv2.IMWRITE_JPEG_QUALITY), 95]))
