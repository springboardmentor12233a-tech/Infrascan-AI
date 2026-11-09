import os
import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.services.inference import classify_damage, generate_gradcam


def test_classify_damage_service():
    # Create test synthetic image
    img = Image.new("RGB", (224, 224), color=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    result = classify_damage(img_bytes)
    assert "has_crack" in result
    assert "confidence_score" in result
    assert "severity_level" in result
    assert result["model_ready"] is True
    assert 0.0 <= result["confidence_score"] <= 1.0


def test_gradcam_service():
    img = Image.new("RGB", (224, 224), color=(150, 150, 150))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    cam_bytes = generate_gradcam(img_bytes)
    assert isinstance(cam_bytes, bytes)
    assert len(cam_bytes) > 0


def test_pdf_report_generation():
    from app.services.reporting import generate_inspection_pdf
    from unittest.mock import MagicMock
    from datetime import datetime

    mock_asset = MagicMock()
    mock_asset.asset_code = "BRG-001"
    mock_asset.name = "Golden Gate Overpass Viaduct"
    mock_asset.asset_type.value = "bridge"
    mock_asset.latitude = 37.8199
    mock_asset.longitude = -122.4783

    mock_insp = MagicMock()
    mock_insp.id = 1
    mock_insp.asset = mock_asset
    mock_insp.scheduled_date = datetime.utcnow()
    mock_insp.status.value = "completed"
    mock_insp.inspector.full_name = "Jane Inspector"

    mock_img = MagicMock()
    mock_img.original_filename = "crack_sample.jpg"
    mock_img.quality_status.value = "ok"
    mock_img.has_crack = True
    mock_img.confidence_score = 0.942
    mock_img.severity_level = "High"
    mock_img.crack_type = "Vertical / Longitudinal Crack"
    mock_img.crack_length_px = 380
    mock_img.max_crack_width_px = 6.4
    mock_img.crack_density_pct = 4.2
    mock_insp.images = [mock_img]

    pdf_bytes = generate_inspection_pdf(mock_insp)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")


def test_segmentation_and_geometry_extraction():
    from app.services.segmentation import segment_crack, extract_crack_geometry_and_boxes, draw_bounding_boxes
    import cv2
    import numpy as np

    # Synthetic image with dark line defect
    img = np.ones((256, 256, 3), dtype=np.uint8) * 200
    cv2.line(img, (50, 40), (60, 220), (30, 30, 30), 4)

    is_success, buf = cv2.imencode(".jpg", img)
    img_bytes = buf.tobytes()

    mask, overlay = segment_crack(img_bytes, has_crack=True)
    assert mask.shape == (256, 256)
    assert overlay.shape == (256, 256, 3)

    geom = extract_crack_geometry_and_boxes(mask, (256, 256))
    assert "crack_length_px" in geom
    assert "max_crack_width_px" in geom
    assert "crack_density_pct" in geom
    assert "crack_type" in geom
    assert "bounding_boxes" in geom
    assert geom["crack_length_px"] > 0
    assert geom["max_crack_width_px"] > 0

    boxes_bytes = draw_bounding_boxes(img_bytes, geom["bounding_boxes"])
    assert isinstance(boxes_bytes, bytes)
    assert len(boxes_bytes) > 0


