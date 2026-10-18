import cv2
import numpy as np
from PIL import Image
import io
from typing import Tuple


def assess_quality(
    image_bytes: bytes,
    blur_threshold: float = 100.0,
    brightness_threshold: float = 50.0
) -> Tuple[float, float, str]:
    """
    Computes blur score (Laplacian variance) and brightness (mean gray value).
    Returns (blur_score, brightness, quality_status: 'ok' | 'blurry' | 'low_light').
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image")

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Blur score using Variance of Laplacian
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # Brightness using mean pixel intensity
    brightness = float(np.mean(gray))

    if blur_score < blur_threshold:
        status = "blurry"
    elif brightness < brightness_threshold:
        status = "low_light"
    else:
        status = "ok"

    return round(blur_score, 2), round(brightness, 2), status


def enhance_image(image_bytes: bytes) -> bytes:
    """
    Applies Gaussian denoising followed by CLAHE (Contrast Limited Adaptive Histogram Equalization).
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image for enhancement")

    # Denoise using Gaussian Blur
    denoised = cv2.GaussianBlur(img_bgr, (3, 3), 0)

    # Convert to LAB color space to apply CLAHE to the Luminance (L) channel
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    merged_lab = cv2.merge((cl, a, b))
    enhanced_bgr = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)

    success, buffer = cv2.imencode(".jpg", enhanced_bgr)
    if not success:
        raise ValueError("Could not encode enhanced image")
    return buffer.tobytes()


def resize_image(image_bytes: bytes, target_size: Tuple[int, int] = (224, 224)) -> bytes:
    """
    Resizes image to target dimensions (e.g., 224x224 standard for AI backbones).
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image for resizing")

    resized = cv2.resize(img_bgr, target_size, interpolation=cv2.INTER_AREA)
    success, buffer = cv2.imencode(".jpg", resized)
    return buffer.tobytes()


def normalize_imagenet(image_bytes: bytes) -> np.ndarray:
    """
    Prepares tensor normalized with standard ImageNet mean and std.
    Placeholder for Milestone 2 AI inference.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(img_rgb, (224, 224))

    # Float conversion [0, 1]
    img_float = resized.astype(np.float32) / 255.0

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    normalized = (img_float - mean) / std
    # Format (C, H, W) for PyTorch / ONNX
    normalized_transposed = np.transpose(normalized, (2, 0, 1))
    return normalized_transposed
