"""Milestone 2 checks that do not require a GPU.

Model-weight tests are skipped when the checkpoint files are absent.
Training metrics are never invented here.
"""

import io
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from app.ml.datasets import parse_cfd_seg, source_group, voc_box_to_yolo
from app.ml.geometry import extract_geometry
from app.ml.paths import CFD_ROOT, CLASSIFIER_WEIGHTS, DEEPCRACK_ROOT, REPO_ROOT
from app.ml.preprocess import preprocess_for_model, resize_keep_aspect, resize_pair
from app.ml.quality import quality_report_from_array, quality_report_from_bytes
from tests.helpers import get_user_token


def test_geometry_of_a_horizontal_crack():
    mask = np.zeros((100, 200), dtype=np.uint8)
    mask[40, 20:120] = 255
    geometry = extract_geometry(mask)
    assert geometry["crack_pixel_area"] == 100
    assert geometry["bbox_width_px"] == 100
    assert geometry["bbox_height_px"] == 1
    assert geometry["coverage_percent"] == 0.5
    assert geometry["crack_length_px"] >= 90
    assert "not millimetres" in geometry["physical_scale_note"]


def test_geometry_empty_mask():
    geometry = extract_geometry(np.zeros((32, 32), dtype=np.uint8))
    assert geometry["crack_pixel_area"] == 0
    assert geometry["coverage_percent"] == 0.0


def test_quality_flags_blur_and_contrast():
    solid = np.full((80, 90, 3), 128, dtype=np.uint8)
    report = quality_report_from_array(solid)
    assert report["valid"] is True
    assert report["width"] == 90
    assert report["height"] == 80
    assert "blurry" in report["flags"]
    assert "low_contrast" in report["flags"]


def test_quality_rejects_invalid_bytes():
    report = quality_report_from_bytes(b"this is not an image")
    assert report["valid"] is False
    assert report["status"] == "invalid"


def test_quality_accepts_a_structured_image():
    image = np.zeros((96, 96, 3), dtype=np.uint8)
    image[:, :48] = 30
    image[:, 48:] = 220
    image[40:50, :] = 255
    report = quality_report_from_array(image)
    assert report["valid"] is True
    assert report["contrast"] > 12


def test_letterbox_preserves_aspect_ratio():
    image = np.zeros((50, 100, 3), dtype=np.uint8)
    image[:, :] = (10, 20, 30)
    canvas, scale, offset = resize_keep_aspect(image, size=(64, 64), pad_value=0)
    assert canvas.shape == (64, 64, 3)
    assert scale == 0.64
    left, top = offset
    assert canvas[0, 0].tolist() == [0, 0, 0]
    assert canvas[top + 1, left + 1].tolist() == [10, 20, 30]


def test_resize_pair_uses_same_output_size():
    image = np.zeros((40, 80, 3), dtype=np.uint8)
    mask = np.zeros((40, 80), dtype=np.uint8)
    mask[10:12, 5:70] = 255
    resized_image, resized_mask = resize_pair(image, mask, (32, 32))
    assert resized_image.shape[:2] == (32, 32)
    assert resized_mask.shape == (32, 32)
    assert set(np.unique(resized_mask)).issubset({0, 255})


def test_grayscale_tensor_has_three_channels():
    gray = np.full((70, 70), 90, dtype=np.uint8)
    tensor = preprocess_for_model(gray, size=(64, 64), keep_aspect=True)
    assert tensor.shape == (3, 64, 64)
    assert tensor.dtype == np.float32


def test_source_group_keeps_deepcrack_crops_together():
    assert source_group("11289-10") == "11289"
    assert source_group("11289-1") == "11289"
    assert source_group("11120") == "11120"


def test_voc_box_converts_to_normalized_yolo():
    box = {"class_id": 0, "xmin": 100, "ymin": 200, "xmax": 300, "ymax": 400}
    converted = voc_box_to_yolo(box, width=600, height=600)
    assert converted is not None
    x_center, y_center, width, height = converted
    assert abs(x_center - (200 / 600)) < 1e-6
    assert abs(y_center - (300 / 600)) < 1e-6
    assert abs(width - (200 / 600)) < 1e-6
    assert abs(height - (200 / 600)) < 1e-6
    assert voc_box_to_yolo({"class_id": None, "xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10}, 100, 100) is None


def test_cfd_seg_parser_when_files_exist():
    seg_dir = CFD_ROOT / "seg"
    if not seg_dir.is_dir():
        for candidate in CFD_ROOT.rglob("*.seg"):
            parsed = parse_cfd_seg(candidate)
            assert parsed["width"] > 0
            assert parsed["crack_fraction"] >= 0
            return
        return
    sample = next(seg_dir.glob("*.seg"), None)
    if sample is None:
        return
    parsed = parse_cfd_seg(sample)
    assert parsed["coverage_complete"] is True


def test_analyze_endpoint_reports_real_status(client: TestClient, db_session):
    token = get_user_token(client, db_session, "Administrator", "admin_m2")
    headers = {"Authorization": f"Bearer {token}"}
    asset = client.post(
        "/assets/",
        json={"asset_code": "M2-ROAD-1", "name": "Demo Road", "type": "Road"},
        headers=headers,
    )
    assert asset.status_code == 201
    me = client.get("/auth/me", headers=headers)
    inspection = client.post(
        "/inspections/",
        json={
            "asset_id": asset.json()["id"],
            "inspector_id": me.json()["id"],
            "inspection_date": "2026-11-02",
        },
        headers=headers,
    )
    assert inspection.status_code == 201
    inspection_id = inspection.json()["id"]

    image = np.zeros((128, 128, 3), dtype=np.uint8)
    image[:, :64] = (20, 20, 20)
    image[:, 64:] = (230, 230, 230)
    image[60:68, :] = (255, 255, 255)
    buffer = io.BytesIO()
    Image.fromarray(image, mode="RGB").save(buffer, format="JPEG")
    buffer.seek(0)
    uploaded = client.post(
        f"/inspections/{inspection_id}/images",
        headers=headers,
        files={"files": ("demo.jpg", buffer, "image/jpeg")},
    )
    assert uploaded.status_code == 201
    image_id = uploaded.json()[0]["id"]

    analyzed = client.post(f"/images/{image_id}/analyze", headers=headers)
    assert analyzed.status_code == 200, analyzed.text
    body = analyzed.json()
    assert body["quality"]["valid"] is True
    assert body["classification_status"] in {"completed", "unavailable", "failed"}
    assert body["detection_status"] in {"completed", "unavailable", "failed"}
    assert body["segmentation_status"] in {"completed", "unavailable", "failed"}
    if body["classification_status"] == "unavailable":
        assert body["classification_label"] is None
    overlay = client.get(f"/images/{image_id}/analysis/overlay", headers=headers)
    assert overlay.status_code == 200
    assert overlay.headers["content-type"].startswith("image/jpeg")

    stats = client.get("/stats", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["images"] >= 1
    assert stats.json()["analyses"] >= 1

    models = client.get("/models/status", headers=headers)
    assert models.status_code == 200
    assert "available" in models.json()["classifier"]


def test_maintenance_cannot_run_analysis(client: TestClient, db_session):
    admin = get_user_token(client, db_session, "Administrator", "admin_m2_deny")
    maintenance = get_user_token(client, db_session, "Maintenance Engineer", "maint_m2_deny")
    admin_headers = {"Authorization": f"Bearer {admin}"}
    asset = client.post(
        "/assets/",
        json={"asset_code": "M2-DENY", "name": "Deny Asset", "type": "Bridge"},
        headers=admin_headers,
    )
    me = client.get("/auth/me", headers=admin_headers)
    inspection = client.post(
        "/inspections/",
        json={
            "asset_id": asset.json()["id"],
            "inspector_id": me.json()["id"],
            "inspection_date": "2026-11-02",
        },
        headers=admin_headers,
    )
    image = Image.new("RGB", (96, 96), color=(10, 200, 10))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    uploaded = client.post(
        f"/inspections/{inspection.json()['id']}/images",
        headers=admin_headers,
        files={"files": ("leaf.jpg", buffer, "image/jpeg")},
    )
    denied = client.post(
        f"/images/{uploaded.json()[0]['id']}/analyze",
        headers={"Authorization": f"Bearer {maintenance}"},
    )
    assert denied.status_code == 403


def test_classifier_forward_when_torch_present():
    try:
        import torch
        from app.ml.nets import SmallCNN, UNet
    except ImportError:
        return
    cnn = SmallCNN()
    unet = UNet(base=8)
    with torch.no_grad():
        logits = cnn(torch.zeros(2, 3, 64, 64))
        mask_logits = unet(torch.zeros(1, 3, 128, 128))
    assert logits.shape == (2, 2)
    assert mask_logits.shape == (1, 1, 128, 128)
    assert CLASSIFIER_WEIGHTS.parent == REPO_ROOT / "models" / "weights"


def test_deepcrack_pair_count_when_present():
    train = DEEPCRACK_ROOT / "train_img"
    if not train.is_dir():
        return
    from app.ml.datasets import list_deepcrack_pairs

    pairs = list_deepcrack_pairs()
    assert len(pairs) == 537
    assert all(pair["image_path"].is_file() and pair["mask_path"].is_file() for pair in pairs[:5])


def test_sample_xml_parses_without_error():
    xml_dir = REPO_ROOT / "datasets" / "raw" / "rdd2022_czech" / "extracted" / "Czech" / "train" / "annotations" / "xmls"
    sample = xml_dir / "Czech_000000.xml"
    if not sample.is_file():
        return
    root = ET.parse(sample).getroot()
    assert root.find("size") is not None
    from app.ml.datasets import parse_voc_xml

    parsed = parse_voc_xml(sample)
    assert parsed["width"] == 600
    assert parsed["height"] == 600
