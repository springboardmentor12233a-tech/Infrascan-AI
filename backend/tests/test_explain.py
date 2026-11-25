"""Pytest test suite for Explainable AI (XAI) attention maps and explanations.

Verifies:
1. Heatmap has the original image size and values strictly between 0 and 1.
2. Two consecutive runs give identical maps (determinism).
3. An empty predicted mask uses the fallback (top 1% pixels) and records the warning.
4. An unsupported model/method pair returns HTTP 400 with a clear message.
5. An inspector without access to an image's inspection receives HTTP 403.
6. A failed explanation does not break or crash the analysis run.
7. The overlay and heatmap endpoints require authentication (login required).
8. Deleting an image removes its associated explanation files from disk.
"""

from datetime import date
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import cv2
import numpy as np
import pytest
import torch
import torch.nn as nn
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.analysis import AnalysisRun, CrackMeasurement, Detection, ModelVersion, run_models
from app.models.asset import InfrastructureAsset
from app.models.audit_log import AuditLog
from app.models.explanation import Explanation
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.user import User
from app.services.security import create_access_token, hash_password
from app.ai.explain import (
    compare_maps,
    explain_detector,
    explain_segmentation,
    generate_color_overlay,
)

TEST_DB_URL = "sqlite:///:memory:"
engine_test = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


# Tiny mocked model architectures for lightning-fast testing without heavy real weights
class TinySegEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        # Conv layer taking 3 input channels (RGB)
        self.layer4 = nn.Sequential(nn.Conv2d(3, 32, kernel_size=3, padding=1))

    def forward(self, x):
        return self.layer4(x)


class TinySegModel(nn.Module):
    def __init__(self, constant_pred=0.0):
        super().__init__()
        self.encoder = TinySegEncoder()
        self.head = nn.Conv2d(32, 1, kernel_size=1)
        self.constant_pred = constant_pred

    def forward(self, x):
        feat = self.encoder(x)
        out = self.head(feat)
        if self.constant_pred is not None:
            # Preserve autograd connection to encoder while shifting logits
            return out + self.constant_pred
        return out


class TinyDetectModule(nn.Module):
    def __init__(self):
        super().__init__()
        # Pre-head feature layer
        self.c2f = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        # Detection head
        self.detect = nn.Conv2d(32, 4, kernel_size=1)

    def __len__(self):
        return 2

    def __getitem__(self, idx):
        if idx in (0, -2):
            return self.c2f
        return self.detect


class TinyYoloModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = TinyDetectModule()

    def forward(self, x):
        feat = self.model.c2f(x)
        out = self.model.detect(feat)
        return (out, {})


@pytest.fixture(scope="function")
def db_session(tmp_path, monkeypatch):
    """Provide isolated db session and temp directories."""
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    masks_dir = tmp_path / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)
    explain_dir = tmp_path / "explanations"
    explain_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(uploads_dir))
    monkeypatch.setattr(settings, "MASK_DIR", str(masks_dir))
    monkeypatch.setattr(settings, "EXPLAIN_DIR", str(explain_dir))

    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def client(db_session, monkeypatch):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.routers.explanations.get_db", override_get_db)
    monkeypatch.setattr("app.routers.images.get_db", override_get_db)
    monkeypatch.setattr("app.routers.analysis.get_db", override_get_db)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user(db, email: str, role: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("Password123!"),
        full_name=f"Test {role}",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_header(user: User) -> dict:
    token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def create_test_setup(db, inspector: User, uploader: User):
    asset = InfrastructureAsset(
        name="Test Bridge XAI",
        asset_type="bridge",
        material_type="concrete",
        address="100 Main St",
        latitude=34.0,
        longitude=-118.0,
        construction_year=2000,
        responsible_department="Bridge Dept",
        inspection_frequency_days=365,
        importance_level="high",
    )
    db.add(asset)
    db.commit()

    inspection = Inspection(
        asset_id=asset.asset_id,
        inspector_id=inspector.user_id,
        inspection_date=date(2026, 11, 1),
        status="in_progress",
    )
    db.add(inspection)
    db.commit()

    # Create dummy image file on disk
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    img_disk_path = upload_path / "test_image.jpg"

    dummy_arr = np.full((120, 160, 3), 128, dtype=np.uint8)
    cv2.imwrite(str(img_disk_path), dummy_arr)

    image = ImageModel(
        inspection_id=inspection.inspection_id,
        uploaded_by=uploader.user_id,
        original_filename="test_image.jpg",
        file_path=str(img_disk_path),
        file_hash="dummyhash1234567890",
        file_size_bytes=1000,
        width_px=160,
        height_px=120,
        quality_status="passed",
    )
    db.add(image)
    db.commit()

    run = AnalysisRun(
        image_id=image.image_id,
        status="done",
        seconds=1.5,
    )
    db.add(run)
    db.commit()

    return asset, inspection, image, run


# ==============================================================================
# TEST 1: Heatmap has original image size and values strictly between 0 and 1
# ==============================================================================
def test_heatmap_shape_and_bounds():
    tiny_model = TinySegModel(constant_pred=1.0)
    img = np.random.randint(0, 256, (120, 160, 3), dtype=np.uint8)

    output = explain_segmentation(
        model=tiny_model,
        img_bgr=img,
        method="gradcam",
        threshold=0.40,
    )

    assert output.heatmap.shape == (120, 160)
    assert output.heatmap.min() >= 0.0
    assert output.heatmap.max() <= 1.0
    assert output.overlay_png is not None
    assert len(output.overlay_png) > 0


# ==============================================================================
# TEST 2: Determinism - Two runs give identical maps
# ==============================================================================
def test_determinism_identical_maps():
    tiny_model = TinySegModel(constant_pred=1.0)
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

    run1 = explain_segmentation(tiny_model, img, method="gradcam")
    run2 = explain_segmentation(tiny_model, img, method="gradcam")

    np.testing.assert_allclose(run1.heatmap, run2.heatmap, atol=1e-6)
    assert run1.overlay_png == run2.overlay_png


# ==============================================================================
# TEST 3: Empty predicted mask uses fallback and records warning
# ==============================================================================
def test_empty_predicted_mask_fallback():
    # Model predicting large negative logits -> sigmoid ~ 0.0001 (below threshold)
    tiny_model = TinySegModel(constant_pred=-10.0)
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

    output = explain_segmentation(tiny_model, img, method="gradcam", threshold=0.50)

    assert len(output.metadata["warnings"]) > 0
    assert any("empty" in w.lower() for w in output.metadata["warnings"])
    assert "top 1%" in output.metadata["target_description"].lower()


# ==============================================================================
# TEST 4: Unsupported model/method pair returns HTTP 400
# ==============================================================================
def test_unsupported_model_method_returns_400(client, db_session):
    admin = create_user(db_session, "admin@infrascan.com", "admin")
    _, _, img, _ = create_test_setup(db_session, admin, admin)

    # Segmentation with 'eigencam' is not supported
    resp = client.post(
        f"/images/{img.image_id}/explain",
        headers=auth_header(admin),
        json={"models": ["unetplusplus_crack500"], "methods": ["eigencam"]},
    )
    assert resp.status_code == 400
    assert "not supported" in resp.json()["detail"].lower()

    # Detector with 'gradcam' is not supported
    resp2 = client.post(
        f"/images/{img.image_id}/explain",
        headers=auth_header(admin),
        json={"models": ["yolov8s_rdd2022"], "methods": ["gradcam"]},
    )
    assert resp2.status_code == 400
    assert "not supported" in resp2.json()["detail"].lower()


# ==============================================================================
# TEST 5: Inspector without access gets HTTP 403
# ==============================================================================
def test_inspector_without_access_forbidden(client, db_session):
    insp1 = create_user(db_session, "insp1@infrascan.com", "inspector")
    insp2 = create_user(db_session, "insp2@infrascan.com", "inspector")
    _, _, img, _ = create_test_setup(db_session, inspector=insp1, uploader=insp1)

    # Inspector 2 attempts to trigger explanation on inspector 1's image
    resp = client.post(
        f"/images/{img.image_id}/explain",
        headers=auth_header(insp2),
        json={"methods": ["gradcam"]},
    )
    assert resp.status_code == 403

    # Inspector 2 attempts to list explanations
    resp2 = client.get(
        f"/images/{img.image_id}/explanations",
        headers=auth_header(insp2),
    )
    assert resp2.status_code == 403


# ==============================================================================
# TEST 6: Failed explanation does not break analysis
# ==============================================================================
def test_failed_explanation_leaves_analysis_intact(client, db_session):
    admin = create_user(db_session, "admin_fail@infrascan.com", "admin")
    _, _, img, run = create_test_setup(db_session, admin, admin)

    # Insert a failed explanation record
    failed_exp = Explanation(
        run_id=run.run_id,
        image_id=img.image_id,
        model_id="unetplusplus_crack500",
        method="gradcam",
        target="mask",
        status="failed",
        error_message="Simulated CUDA out of memory error during explanation",
    )
    db_session.add(failed_exp)
    db_session.commit()

    # Query analysis run
    resp = client.get(f"/images/{img.image_id}/analysis", headers=auth_header(admin))
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"  # Analysis run is still completely valid and 'done'

    # Query explanations
    exp_resp = client.get(f"/images/{img.image_id}/explanations", headers=auth_header(admin))
    assert exp_resp.status_code == 200
    items = exp_resp.json()
    assert len(items) == 1
    assert items[0]["status"] == "failed"
    assert "Simulated" in items[0]["error_message"]


# ==============================================================================
# TEST 7: Overlay and heatmap endpoints need login (401 without auth)
# ==============================================================================
def test_overlay_and_heatmap_require_auth(client, db_session):
    admin = create_user(db_session, "admin_auth@infrascan.com", "admin")
    _, _, img, run = create_test_setup(db_session, admin, admin)

    # Create dummy files
    exp_dir = Path(settings.EXPLAIN_DIR)
    exp_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = exp_dir / "test_overlay.png"
    heatmap_path = exp_dir / "test_heat.npy"

    cv2.imwrite(str(overlay_path), np.zeros((100, 100, 3), dtype=np.uint8))
    np.save(str(heatmap_path), np.zeros((100, 100), dtype=np.float32))

    exp = Explanation(
        run_id=run.run_id,
        image_id=img.image_id,
        model_id="unetplusplus_crack500",
        method="gradcam",
        target="mask",
        overlay_path=f"{settings.EXPLAIN_DIR}/test_overlay.png",
        heatmap_path=f"{settings.EXPLAIN_DIR}/test_heat.npy",
        status="done",
    )
    db_session.add(exp)
    db_session.commit()

    # Unauthenticated GET
    resp_unauth_ov = client.get(f"/explanations/{exp.explanation_id}/overlay")
    assert resp_unauth_ov.status_code == 401

    resp_unauth_hm = client.get(f"/explanations/{exp.explanation_id}/heatmap")
    assert resp_unauth_hm.status_code == 401

    # Authenticated GET
    resp_auth_ov = client.get(
        f"/explanations/{exp.explanation_id}/overlay", headers=auth_header(admin)
    )
    assert resp_auth_ov.status_code == 200
    assert resp_auth_ov.headers["content-type"] == "image/png"


# ==============================================================================
# TEST 8: Deleting an image removes its explanation files from disk
# ==============================================================================
def test_delete_image_removes_explanation_files(client, db_session):
    admin = create_user(db_session, "admin_del@infrascan.com", "admin")
    _, _, img, run = create_test_setup(db_session, admin, admin)

    exp_dir = Path(settings.EXPLAIN_DIR)
    exp_dir.mkdir(parents=True, exist_ok=True)
    overlay_file = exp_dir / f"del_test_overlay_{img.image_id}.png"
    heatmap_file = exp_dir / f"del_test_heat_{img.image_id}.npy"

    cv2.imwrite(str(overlay_file), np.zeros((50, 50, 3), dtype=np.uint8))
    np.save(str(heatmap_file), np.zeros((50, 50), dtype=np.float32))

    assert overlay_file.exists()
    assert heatmap_file.exists()

    exp = Explanation(
        run_id=run.run_id,
        image_id=img.image_id,
        model_id="unetplusplus_crack500",
        method="gradcam",
        target="mask",
        overlay_path=str(overlay_file),
        heatmap_path=str(heatmap_file),
        status="done",
    )
    db_session.add(exp)
    db_session.commit()

    # Delete image via DELETE /images/{id}
    del_resp = client.delete(f"/images/{img.image_id}", headers=auth_header(admin))
    assert del_resp.status_code == 200

    # Verify physical explanation files were deleted from disk
    assert not overlay_file.exists()
    assert not heatmap_file.exists()
