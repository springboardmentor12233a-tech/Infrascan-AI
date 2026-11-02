"""Reusable image preprocessing for quality checks and model input.

Geometric steps that must stay aligned (image and mask) live in
`resize_pair` and `apply_same_flip`. Model networks receive a CHW float tensor.
"""

from __future__ import annotations

import io
from typing import Optional, Tuple

import cv2
import numpy as np

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def decode_image(image_bytes: bytes) -> np.ndarray:
    """Decode bytes to a BGR or grayscale ndarray. Raises ValueError if invalid."""
    if not image_bytes:
        raise ValueError("Empty image bytes")
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError("Could not decode image")
    return image


def load_bgr(path: str) -> np.ndarray:
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def to_bgr(image: np.ndarray) -> np.ndarray:
    """Return a 3-channel BGR image. Grayscale and BGRA inputs are converted."""
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 1:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def to_rgb(image: np.ndarray) -> np.ndarray:
    bgr = to_bgr(image)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    bgr = to_bgr(image)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def denoise(image: np.ndarray, kernel: int = 3) -> np.ndarray:
    """Light Gaussian denoise. Off by default for crack models because cracks are thin."""
    if kernel % 2 == 0:
        kernel += 1
    return cv2.GaussianBlur(image, (kernel, kernel), 0)


def resize_keep_aspect(
    image: np.ndarray,
    size: Tuple[int, int] = (224, 224),
    pad_value: int = 0,
) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """Letterbox resize. `size` is (width, height). Returns image, scale, (left, top)."""
    target_w, target_h = size
    bgr = to_bgr(image)
    height, width = bgr.shape[:2]
    if height == 0 or width == 0:
        raise ValueError("Image has a zero dimension")
    scale = min(target_w / width, target_h / height)
    new_w = max(1, int(round(width * scale)))
    new_h = max(1, int(round(height * scale)))
    resized = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    canvas = np.full((target_h, target_w, 3), pad_value, dtype=resized.dtype)
    left = (target_w - new_w) // 2
    top = (target_h - new_h) // 2
    canvas[top : top + new_h, left : left + new_w] = resized
    return canvas, float(scale), (left, top)


def resize_stretch(image: np.ndarray, size: Tuple[int, int], interpolation: int = cv2.INTER_AREA) -> np.ndarray:
    """Resize to (width, height) without preserving aspect ratio."""
    return cv2.resize(image, size, interpolation=interpolation)


def resize_pair(
    image: np.ndarray,
    mask: np.ndarray,
    size: Tuple[int, int],
) -> Tuple[np.ndarray, np.ndarray]:
    """Resize an image and its mask with the same output size.

    The image uses area interpolation. The mask uses nearest-neighbour so
    crack labels are not blurred into gray values.
    """
    image_out = resize_stretch(to_bgr(image), size, interpolation=cv2.INTER_AREA)
    mask_gray = mask if mask.ndim == 2 else to_gray(mask)
    mask_out = resize_stretch(mask_gray, size, interpolation=cv2.INTER_NEAREST)
    return image_out, mask_out


def apply_same_flip(
    image: np.ndarray,
    mask: Optional[np.ndarray] = None,
    horizontal: bool = False,
    vertical: bool = False,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Flip an image and, when present, its mask with the same axes."""
    code = None
    if horizontal and vertical:
        code = -1
    elif horizontal:
        code = 1
    elif vertical:
        code = 0
    if code is None:
        return image, mask
    flipped = cv2.flip(image, code)
    flipped_mask = cv2.flip(mask, code) if mask is not None else None
    return flipped, flipped_mask


def normalize_rgb(rgb: np.ndarray, imagenet: bool = True) -> np.ndarray:
    """HWC uint8 or float RGB -> HWC float32, optionally ImageNet-normalized."""
    array = rgb.astype(np.float32)
    if array.max() > 1.5:
        array = array / 255.0
    if imagenet:
        array = (array - IMAGENET_MEAN) / IMAGENET_STD
    return array


def to_chw(hwc: np.ndarray) -> np.ndarray:
    return np.transpose(hwc, (2, 0, 1)).astype(np.float32)


def preprocess_for_model(
    image: np.ndarray,
    size: Tuple[int, int] = (64, 64),
    imagenet: bool = True,
    keep_aspect: bool = True,
    reduce_noise: bool = False,
) -> np.ndarray:
    """Validate, optionally denoise, resize, normalize, and return a CHW tensor.

    Accepts grayscale or color images. Output always has 3 channels.
    """
    if image is None or image.size == 0:
        raise ValueError("Empty image")
    if image.ndim not in (2, 3):
        raise ValueError(f"Unsupported image shape {image.shape}")
    working = to_bgr(image)
    if reduce_noise:
        working = denoise(working)
    if keep_aspect:
        working, _, _ = resize_keep_aspect(working, size=size)
    else:
        working = resize_stretch(working, size)
    rgb = cv2.cvtColor(working, cv2.COLOR_BGR2RGB)
    return to_chw(normalize_rgb(rgb, imagenet=imagenet))


def encode_jpeg(image_bgr: np.ndarray, quality: int = 90) -> bytes:
    ok, buffer = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("Could not encode JPEG")
    return buffer.tobytes()


def encode_png(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode PNG")
    return buffer.tobytes()


def read_upload(image_bytes: bytes) -> np.ndarray:
    """Decode an upload and return BGR. Wraps decode errors as ValueError."""
    try:
        image = decode_image(image_bytes)
    except Exception as exc:
        raise ValueError("Invalid or corrupt image") from exc
    return to_bgr(image)


def tensor_from_bytes(image_bytes: bytes, size: Tuple[int, int] = (224, 224)) -> np.ndarray:
    image = read_upload(image_bytes)
    return preprocess_for_model(image, size=size, imagenet=True, keep_aspect=True, reduce_noise=False)
