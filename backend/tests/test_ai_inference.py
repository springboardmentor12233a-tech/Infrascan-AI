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
    mock_insp.images = [mock_img]

    pdf_bytes = generate_inspection_pdf(mock_insp)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")

