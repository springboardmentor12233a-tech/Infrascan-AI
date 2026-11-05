"""
Pytest suite for the image preprocessing pipeline.

Tests:
1. Output shape is (256, 256, 3)
2. zero_one normalized values are strictly within [0.0, 1.0]
3. imagenet normalization produces different values than zero_one
4. Non-square images preserve aspect ratio with letterbox padding
5. Original file is unchanged after processing (SHA-256 comparison)
6. Disabled pipeline steps do not appear in steps_applied
"""

import hashlib
import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest

from app.ai.preprocessing import (
    PreprocessConfig,
    PreprocessResult,
    preprocess,
    save_enhanced,
    to_tiles,
)


@pytest.fixture
def sample_bgr_image() -> np.ndarray:
    """Generate a synthetic 480x640 BGR image with simulated texture and gradient."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add gradient and high contrast lines simulating concrete cracks
    for r in range(480):
        img[r, :, :] = (r % 256, (r * 2) % 256, (r * 3) % 256)
    # Simulated crack lines (dark pixels)
    img[100:350, 200:205] = [20, 20, 20]
    return img


# 1. Output shape is (256, 256, 3)
def test_output_shape(sample_bgr_image):
    config = PreprocessConfig(model_input_size=256)
    result = preprocess(sample_bgr_image, config=config)

    assert isinstance(result, PreprocessResult)
    assert result.model_input.shape == (256, 256, 3)
    assert result.model_size == (256, 256)
    assert result.original_size == (480, 640)
    assert result.enhanced_image.shape == sample_bgr_image.shape


# 2. zero_one values are between 0 and 1
def test_zero_one_values(sample_bgr_image):
    config = PreprocessConfig(model_input_size=256, normalize_mode="zero_one")
    result = preprocess(sample_bgr_image, config=config)

    assert result.model_input.dtype == np.float32
    assert float(result.model_input.min()) >= 0.0
    assert float(result.model_input.max()) <= 1.0
    assert "normalize_zero_one" in result.steps_applied


# 3. imagenet mode gives different values than zero_one
def test_imagenet_mode_differs_from_zero_one(sample_bgr_image):
    res_zero = preprocess(
        sample_bgr_image,
        config=PreprocessConfig(model_input_size=256, normalize_mode="zero_one"),
    )
    res_imagenet = preprocess(
        sample_bgr_image,
        config=PreprocessConfig(model_input_size=256, normalize_mode="imagenet"),
    )

    assert res_zero.model_input.shape == res_imagenet.model_input.shape
    # ImageNet normalization standardizes with mean and std, resulting in negative & positive values
    assert not np.allclose(res_zero.model_input, res_imagenet.model_input)
    assert "normalize_imagenet" in res_imagenet.steps_applied
    assert "normalize_zero_one" in res_zero.steps_applied
    assert float(res_imagenet.model_input.min()) < 0.0


# 4. A non-square image keeps its aspect ratio (padding present)
def test_aspect_ratio_padding():
    # Wide image: height=100, width=500 (aspect ratio 5:1)
    wide_img = np.full((100, 500, 3), 180, dtype=np.uint8)
    config = PreprocessConfig(model_input_size=256, normalize_mode="zero_one")
    result = preprocess(wide_img, config=config)

    assert result.model_input.shape == (256, 256, 3)
    pad_info = result.pad_info

    # In a 5:1 wide image fitted into 256x256, top and bottom must have black padding
    assert pad_info["pad_top"] > 0
    assert pad_info["pad_bottom"] > 0
    assert pad_info["pad_left"] == 0
    assert pad_info["pad_right"] == 0

    # Top border row and bottom border row should be pure black [0, 0, 0]
    assert np.all(result.model_input[0, :, :] == 0.0)
    assert np.all(result.model_input[-1, :, :] == 0.0)

    # Center row should contain image data (non-zero)
    center_y = 128
    assert np.any(result.model_input[center_y, :, :] > 0.0)


# 5. Original file is unchanged after processing (compare hashes)
def test_original_file_unchanged(sample_bgr_image):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        orig_file = tmp_path / "original_crack.jpg"
        enhanced_file = tmp_path / "enhanced_crack.jpg"

        # Save sample image as original file
        cv2.imwrite(str(orig_file), sample_bgr_image)
        with open(orig_file, "rb") as f:
            hash_before = hashlib.sha256(f.read()).hexdigest()

        # Read, preprocess, and save enhanced copy to different location
        read_img = cv2.imread(str(orig_file))
        result = preprocess(read_img, PreprocessConfig())
        save_enhanced(enhanced_file, result.enhanced_image)

        # Re-check original file hash
        with open(orig_file, "rb") as f:
            hash_after = hashlib.sha256(f.read()).hexdigest()

        assert hash_before == hash_after, "Original file was modified during preprocessing!"
        assert enhanced_file.exists()


# 6. A disabled step does not appear in steps_applied
def test_disabled_step_not_in_steps_applied(sample_bgr_image):
    # Disable contrast, denoise, and sharpen
    config_disabled = PreprocessConfig(
        enable_contrast=False,
        enable_denoise=False,
        enable_sharpen=False,
    )
    result_disabled = preprocess(sample_bgr_image, config=config_disabled)

    assert "contrast_clahe" not in result_disabled.steps_applied
    assert "denoise" not in result_disabled.steps_applied
    assert "sharpen" not in result_disabled.steps_applied

    # Enable contrast only
    config_enabled = PreprocessConfig(
        enable_contrast=True,
        enable_denoise=False,
        enable_sharpen=False,
    )
    result_enabled = preprocess(sample_bgr_image, config=config_enabled)
    assert "contrast_clahe" in result_enabled.steps_applied
    assert "denoise" not in result_enabled.steps_applied


# Helper test: to_tiles and save_enhanced
def test_to_tiles_and_save_enhanced(sample_bgr_image):
    tiles = to_tiles(sample_bgr_image, tile_size=256, overlap=32)
    assert len(tiles) > 0
    tile0, coords0 = tiles[0]
    assert tile0.shape == (256, 256, 3)
    assert len(coords0) == 4

    with tempfile.TemporaryDirectory() as tmp_dir:
        dest = Path(tmp_dir) / "sub" / "tile0.jpg"
        ok = save_enhanced(dest, tile0)
        assert ok is True
        assert dest.exists()


# Endpoint test: trigger preprocess and fetch processed image
def test_preprocess_endpoint(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from datetime import date
    from app.config import settings
    from app.database import Base, get_db
    from app.main import app
    from app.models.asset import InfrastructureAsset
    from app.models.image import Image as ImageModel
    from app.models.inspection import Inspection
    from app.models.user import User
    from app.services.security import hash_password

    # Configure temporary directories
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "PROCESSED_DIR", str(tmp_path / "processed"))

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSession()

    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db

    try:
        # Create inspector and admin
        inspector = User(
            full_name="Inspector Test",
            email="inspector_prep@test.com",
            password_hash=hash_password("Pass12345"),
            role="inspector",
            is_active=True,
        )
        admin = User(
            full_name="Admin Test",
            email="admin_prep@test.com",
            password_hash=hash_password("Pass12345"),
            role="admin",
            is_active=True,
        )
        db.add_all([inspector, admin])
        db.commit()

        asset = InfrastructureAsset(
            name="Bridge Prep",
            asset_type="bridge",
            material_type="concrete",
            address="123 Road",
            latitude=12.0,
            longitude=77.0,
            construction_year=2010,
            responsible_department="PWD",
            inspection_frequency_days=90,
            importance_level="high",
            created_by=admin.user_id,
        )
        db.add(asset)
        db.commit()

        inspection = Inspection(
            asset_id=asset.asset_id,
            inspector_id=inspector.user_id,
            inspection_date=date.today(),
            status="assigned",
        )
        db.add(inspection)
        db.commit()

        # Create dummy image file on disk
        upload_folder = tmp_path / "uploads" / str(inspection.inspection_id)
        upload_folder.mkdir(parents=True, exist_ok=True)
        img_disk_path = upload_folder / "orig.jpg"
        dummy_cv_img = np.full((480, 640, 3), 120, dtype=np.uint8)
        cv2.imwrite(str(img_disk_path), dummy_cv_img)

        image_rec = ImageModel(
            inspection_id=inspection.inspection_id,
            uploaded_by=inspector.user_id,
            file_path=str(img_disk_path),
            original_filename="orig.jpg",
            file_hash="dummy_hash_12345",
            width_px=640,
            height_px=480,
            file_size_bytes=1000,
            source="phone",
            blur_score=150.0,
            brightness_score=120.0,
            quality_status="passed",
            preprocess_status="not_run",
        )
        db.add(image_rec)
        db.commit()
        db.refresh(image_rec)

        with TestClient(app) as client:
            # Login as inspector
            login_resp = client.post(
                "/auth/login",
                data={"username": "inspector_prep@test.com", "password": "Pass12345"},
            )
            token = login_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 1. Trigger preprocessing
            prep_resp = client.post(f"/images/{image_rec.image_id}/preprocess", headers=headers)
            assert prep_resp.status_code == 200
            data = prep_resp.json()
            assert data["preprocess_status"] == "done"
            assert "contrast_clahe" in data["preprocess_steps"]

            # 2. Fetch processed image file
            file_resp = client.get(f"/images/{image_rec.image_id}/processed", headers=headers)
            assert file_resp.status_code == 200
            assert file_resp.headers["content-type"] == "image/jpeg"

            # 3. Trigger inspection-wide preprocessing with admin token
            admin_login = client.post(
                "/auth/login",
                data={"username": "admin_prep@test.com", "password": "Pass12345"},
            )
            admin_token = admin_login.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            insp_prep_resp = client.post(
                f"/inspections/{inspection.inspection_id}/preprocess", headers=admin_headers
            )
            assert insp_prep_resp.status_code == 200
            assert len(insp_prep_resp.json()) == 1
    finally:
        app.dependency_overrides.clear()
        db.close()
