import cv2
import numpy as np
from PIL import Image
import io
from typing import Tuple, Dict, Any


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
    elif brightness > 230:
        status = "overexposed"
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

    denoised = cv2.GaussianBlur(img_bgr, (3, 3), 0)
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


def sharpen_image(image_bytes: bytes) -> bytes:
    """
    Applies unsharp masking to enhance fine micro-cracks and structural fissures.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image for sharpening")

    gaussian = cv2.GaussianBlur(img_bgr, (0, 0), 2.0)
    unsharp = cv2.addWeighted(img_bgr, 1.6, gaussian, -0.6, 0)
    success, buffer = cv2.imencode(".jpg", unsharp)
    return buffer.tobytes()


def shadow_reduction(image_bytes: bytes) -> bytes:
    """
    Mitigates harsh shadows cast by bridge girders, rebar, or sun angles
    using morphological illumination estimation and division normalization.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image for shadow reduction")

    dilated = cv2.dilate(img_bgr, np.ones((7, 7), np.uint8))
    bg_img = cv2.medianBlur(dilated, 21)
    diff = 255 - cv2.absdiff(img_bgr, bg_img)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)

    success, buffer = cv2.imencode(".jpg", norm)
    return buffer.tobytes()


def edge_enhancement(image_bytes: bytes) -> bytes:
    """
    Extracts structural surface edges and crack boundary contours using Canny & Sobel gradients.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image for edge enhancement")

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 40, 120)

    # Colorize edges on a semi-transparent dark background
    edge_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    edge_bgr[edges > 0] = [0, 255, 255]  # Bright yellow edges
    blended = cv2.addWeighted(img_bgr, 0.65, edge_bgr, 0.35, 0)

    success, buffer = cv2.imencode(".jpg", blended)
    return buffer.tobytes()


def texture_enhancement(image_bytes: bytes) -> bytes:
    """
    Highlights concrete aggregate textures and spalling roughness using high-pass filtering.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image for texture enhancement")

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
    textured = cv2.filter2D(gray, -1, kernel)
    textured_bgr = cv2.cvtColor(textured, cv2.COLOR_GRAY2BGR)

    success, buffer = cv2.imencode(".jpg", textured_bgr)
    return buffer.tobytes()


def roi_extraction(image_bytes: bytes) -> bytes:
    """
    Removes sky/distant backgrounds and isolates the central concrete surface ROI.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image for ROI extraction")

    h, w = img_bgr.shape[:2]
    # Crop central 85% region to eliminate boundary artifacts
    pad_h, pad_w = int(h * 0.075), int(w * 0.075)
    roi = img_bgr[pad_h:h - pad_h, pad_w:w - pad_w]
    roi_resized = cv2.resize(roi, (w, h), interpolation=cv2.INTER_LINEAR)

    success, buffer = cv2.imencode(".jpg", roi_resized)
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
    Prepares tensor normalized with standard ImageNet mean and std for model inference.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(img_rgb, (224, 224))

    img_float = resized.astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    normalized = (img_float - mean) / std
    return np.transpose(normalized, (2, 0, 1))
