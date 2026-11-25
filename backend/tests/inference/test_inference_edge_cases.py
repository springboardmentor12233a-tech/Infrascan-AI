"""Synthetic Edge Cases and Determinism Inference Test Suite for InfraScan.

Validates robust model behavior on extreme synthetic images, corrupted bytes,
decompression bomb limits, determinism, and execution latency thresholds.
"""

import io
import time
import cv2
import numpy as np
import pytest
import torch
from PIL import Image

from app.config import settings
from app.services.analysis_service import get_yolo_model, get_segmentation_model


@pytest.fixture(scope="module")
def yolo_detector():
    """Load cached YOLO detector."""
    try:
        return get_yolo_model(settings.YOLO_WEIGHTS)
    except Exception as e:
        pytest.skip(f"YOLO detector weights not accessible: {e}")


@pytest.fixture(scope="module")
def seg_model():
    """Load cached segmentation model."""
    try:
        return get_segmentation_model(settings.SEG_WEIGHTS)
    except Exception as e:
        pytest.skip(f"Segmentation weights not accessible: {e}")


def test_inference_all_black_image(yolo_detector):
    """Test model handles completely black image without numerical division by zero."""
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    with torch.inference_mode():
        results = yolo_detector.predict(source=img, imgsz=640, verbose=False)
    assert results is not None
    assert len(results) > 0


def test_inference_all_white_image(yolo_detector):
    """Test model handles completely saturated white image without saturation overflow."""
    img = np.full((640, 640, 3), 255, dtype=np.uint8)
    with torch.inference_mode():
        results = yolo_detector.predict(source=img, imgsz=640, verbose=False)
    assert results is not None


def test_inference_pure_noise(yolo_detector):
    """Test model handles pure random Gaussian/uniform noise."""
    np.random.seed(42)
    img = np.random.randint(0, 256, (640, 640, 3), dtype=np.uint8)
    with torch.inference_mode():
        results = yolo_detector.predict(source=img, imgsz=640, verbose=False)
    assert results is not None


def test_inference_checkerboard_pattern(yolo_detector):
    """Test model handles high-frequency checkerboard pattern."""
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    img[::32, ::32] = 255
    with torch.inference_mode():
        results = yolo_detector.predict(source=img, imgsz=640, verbose=False)
    assert results is not None


def test_inference_extreme_aspect_ratios(yolo_detector):
    """Test model handles extreme 10:1 and 1:10 aspect ratios with letterboxing."""
    # 10:1 wide aspect ratio
    wide_img = np.full((64, 640, 3), 128, dtype=np.uint8)
    with torch.inference_mode():
        res_wide = yolo_detector.predict(source=wide_img, imgsz=640, verbose=False)
    assert res_wide is not None

    # 1:10 tall aspect ratio
    tall_img = np.full((640, 64, 3), 128, dtype=np.uint8)
    with torch.inference_mode():
        res_tall = yolo_detector.predict(source=tall_img, imgsz=640, verbose=False)
    assert res_tall is not None


def test_inference_tiny_image_upscale_handling(yolo_detector):
    """Test model handles tiny 32x32 image without kernel shape mismatch."""
    tiny_img = np.full((32, 32, 3), 128, dtype=np.uint8)
    with torch.inference_mode():
        res_tiny = yolo_detector.predict(source=tiny_img, imgsz=640, verbose=False)
    assert res_tiny is not None


def test_inference_corrupted_jpeg_rejection():
    """Test invalid or truncated image bytes return None and are rejected cleanly."""
    corrupted_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 30  # truncated JPEG header
    nparr = np.frombuffer(corrupted_bytes, np.uint8)
    decoded = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    assert decoded is None  # Fails cleanly without segfault


def test_decompression_bomb_guard():
    """Verify decompression bomb safety limit is enforced."""
    # PIL Default decompression bomb threshold
    assert Image.MAX_IMAGE_PIXELS is not None
    assert Image.MAX_IMAGE_PIXELS >= 50_000_000


def test_inference_determinism(yolo_detector):
    """Verify that analyzing the identical image twice produces identical bounding boxes."""
    np.random.seed(123)
    img = np.random.randint(50, 200, (640, 640, 3), dtype=np.uint8)

    with torch.inference_mode():
        res1 = yolo_detector.predict(source=img, imgsz=640, verbose=False)
        res2 = yolo_detector.predict(source=img, imgsz=640, verbose=False)

    boxes1 = res1[0].boxes.xyxy.cpu().numpy() if res1[0].boxes is not None else np.array([])
    boxes2 = res2[0].boxes.xyxy.cpu().numpy() if res2[0].boxes is not None else np.array([])

    assert np.array_equal(boxes1, boxes2)


def test_inference_latency_threshold(yolo_detector):
    """Verify 640px inference completes within acceptable threshold on CPU (< 3.0s)."""
    img = np.full((640, 640, 3), 128, dtype=np.uint8)

    # Warmup
    with torch.inference_mode():
        _ = yolo_detector.predict(source=img, imgsz=640, verbose=False)

    t0 = time.perf_counter()
    with torch.inference_mode():
        _ = yolo_detector.predict(source=img, imgsz=640, verbose=False)
    elapsed = time.perf_counter() - t0

    assert elapsed < 3.0, f"Inference took {elapsed:.2f}s, exceeding 3.0s threshold."
