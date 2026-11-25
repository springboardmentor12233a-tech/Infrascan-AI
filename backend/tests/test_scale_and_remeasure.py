"""
Pytest suite for physical scale configuration and remeasurement logic (Milestone 3, Step 2).

Tests:
1. Scale from two points is exact (e.g. 200 px for 100 mm gives 0.5 mm/px).
2. 100 px at 0.5 mm/px gives 50 mm, and uncertainty is positive.
3. Zero, negative, and too-short references (< 100 px) are rejected with clear 400 errors.
4. No scale gives null mm fields.
5. Remeasure does not call any deep learning models (mocked & asserted).
6. Permissions: an unrelated inspector gets 403 on PUT, DELETE, and POST remeasure.
7. Replacing a scale keeps the old row with is_current=False while the new row is is_current=True.
"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.analysis import AnalysisRun, CrackMeasurement, ImageScale
from app.models.asset import InfrastructureAsset
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.user import User
import app.services.analysis_service as analysis_service_mod
from app.services.security import create_access_token, hash_password

# In-memory isolated test database
TEST_DB_URL = "sqlite:///:memory:"
engine_test = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function")
def db_session(tmp_path, monkeypatch):
    """Provide isolated db session and temp directories."""
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    masks_dir = tmp_path / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(uploads_dir))
    monkeypatch.setattr(settings, "MASK_DIR", str(masks_dir))

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
    monkeypatch.setattr("app.routers.analysis.SessionLocal", TestingSessionLocal)
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


def create_test_asset(db, name="Bridge S") -> InfrastructureAsset:
    asset = InfrastructureAsset(
        name=name,
        asset_type="bridge",
        material_type="concrete",
        address="100 Scale Way",
        latitude=13.0,
        longitude=80.0,
        construction_year=2021,
        responsible_department="PWD",
        inspection_frequency_days=90,
        importance_level="high",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def create_dummy_image_file(path: Path, width=800, height=600):
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    img.save(str(path))


def setup_test_image(db, tmp_path, uploader: User) -> ImageModel:
    asset = create_test_asset(db)
    inspection = Inspection(asset_id=asset.asset_id, inspector_id=uploader.user_id, inspection_date=date.today())
    db.add(inspection)
    db.commit()

    img_file = tmp_path / "uploads" / "scale_test.jpg"
    create_dummy_image_file(img_file, 800, 600)

    image = ImageModel(
        inspection_id=inspection.inspection_id,
        uploaded_by=uploader.user_id,
        file_path=str(img_file),
        original_filename="scale_test.jpg",
        file_hash="dummy_scale_hash",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


# ---------------------------------------------------------------------------
# TEST 1: Scale from two points is exact (200 px for 100 mm -> 0.5 mm/px)
# ---------------------------------------------------------------------------
def test_scale_from_two_points_is_exact(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_scale1@test.com", "admin")
    image = setup_test_image(db_session, tmp_path, admin)

    payload = {
        "point1": [100.0, 100.0],
        "point2": [100.0, 300.0],  # dy = 200 px, dx = 0 px -> 200 px distance
        "reference_mm": 100.0,
        "camera_perpendicular": True,
    }

    res = client.put(f"/images/{image.image_id}/scale", json=payload, headers=auth_headers(admin))
    assert res.status_code == 200
    data = res.json()

    assert data["method"] == "reference_object"
    assert data["reference_px"] == 200.0
    assert data["reference_mm"] == 100.0
    assert data["mm_per_pixel"] == 0.5  # 100 / 200 = 0.5 mm/px exactly
    assert data["uncertainty_percent"] > 0
    # uncertainty_percent = 100 * sqrt(2) / 200 = 0.7071%
    assert abs(data["uncertainty_percent"] - (100.0 * (2 ** 0.5) / 200.0)) < 0.001
    assert data["camera_perpendicular"] is True
    assert data["is_current"] is True


# ---------------------------------------------------------------------------
# TEST 2: 100 px at 0.5 mm/px gives 50 mm, and uncertainty is positive
# ---------------------------------------------------------------------------
def test_100px_at_half_mm_per_px_gives_50mm(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_scale2@test.com", "admin")
    image = setup_test_image(db_session, tmp_path, admin)

    # 1. Create completed analysis run with 100 px crack length
    run = AnalysisRun(image_id=image.image_id, status="done")
    db_session.add(run)
    db_session.commit()

    meas = CrackMeasurement(
        run_id=run.run_id,
        mask_path="dummy_mask.png",
        threshold=0.40,
        crack_pixels=500,
        length_px=100.0,
        avg_width_px=4.0,
        max_width_px=8.0,
        p95_width_px=7.0,
        area_px=500,
        density_percent=0.1,
        orientation_deg=45.0,
        num_components=1,
        num_branch_points=0,
        num_end_points=2,
        width_mode="edt2",
    )
    db_session.add(meas)
    db_session.commit()

    # 2. Set scale: 200 px = 100 mm -> 0.5 mm/px
    scale_payload = {
        "point1": [0.0, 0.0],
        "point2": [200.0, 0.0],
        "reference_mm": 100.0,
        "camera_perpendicular": True,
    }
    res_scale = client.put(f"/images/{image.image_id}/scale", json=scale_payload, headers=auth_headers(admin))
    assert res_scale.status_code == 200

    # 3. Call POST /images/{id}/remeasure
    res_rem = client.post(f"/images/{image.image_id}/remeasure", headers=auth_headers(admin))
    assert res_rem.status_code == 200
    rem_data = res_rem.json()

    assert len(rem_data["crack_measurements"]) == 1
    m = rem_data["crack_measurements"][0]

    # length_mm = 100 px * 0.5 mm/px = 50.0 mm
    assert m["length_mm"] == 50.0
    # avg_width_mm = 4.0 px * 0.5 mm/px = 2.0 mm
    assert m["avg_width_mm"] == 2.0
    # max_width_mm = 8.0 px * 0.5 mm/px = 4.0 mm
    assert m["max_width_mm"] == 4.0
    assert m["mm_per_pixel"] == 0.5

    # Uncertainty must be strictly positive
    assert m["length_mm_uncertainty"] is not None
    assert m["length_mm_uncertainty"] > 0
    assert m["width_mm_uncertainty"] is not None
    assert m["width_mm_uncertainty"] > 0
    assert m["measurement_note"] is None  # perpendicular was True


# ---------------------------------------------------------------------------
# TEST 3: Zero, negative, and too-short references (< 100 px) are rejected
# ---------------------------------------------------------------------------
def test_zero_negative_and_too_short_references_are_rejected(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_scale3@test.com", "admin")
    image = setup_test_image(db_session, tmp_path, admin)

    # a. Zero reference_mm
    res_zero = client.put(f"/images/{image.image_id}/scale", json={
        "point1": [0.0, 0.0], "point2": [0.0, 200.0], "reference_mm": 0.0, "camera_perpendicular": True
    }, headers=auth_headers(admin))
    assert res_zero.status_code == 400

    # b. Negative reference_mm
    res_neg = client.put(f"/images/{image.image_id}/scale", json={
        "point1": [0.0, 0.0], "point2": [0.0, 200.0], "reference_mm": -100.0, "camera_perpendicular": True
    }, headers=auth_headers(admin))
    assert res_neg.status_code == 400

    # c. Too short reference (< 100 px, e.g. 50 px)
    res_short = client.put(f"/images/{image.image_id}/scale", json={
        "point1": [0.0, 0.0], "point2": [0.0, 50.0], "reference_mm": 25.0, "camera_perpendicular": True
    }, headers=auth_headers(admin))
    assert res_short.status_code == 400
    assert "at least 100 pixels" in res_short.json()["detail"]

    # d. Negative or zero mm_per_pixel
    res_bad_ratio = client.put(f"/images/{image.image_id}/scale", json={
        "mm_per_pixel": -0.5, "camera_perpendicular": True
    }, headers=auth_headers(admin))
    assert res_bad_ratio.status_code == 400

    # e. Out of bounds mm_per_pixel (< 0.01 or > 20.0)
    res_tiny_ratio = client.put(f"/images/{image.image_id}/scale", json={
        "mm_per_pixel": 0.001, "camera_perpendicular": True
    }, headers=auth_headers(admin))
    assert res_tiny_ratio.status_code == 400

    res_huge_ratio = client.put(f"/images/{image.image_id}/scale", json={
        "mm_per_pixel": 25.0, "camera_perpendicular": True
    }, headers=auth_headers(admin))
    assert res_huge_ratio.status_code == 400


# ---------------------------------------------------------------------------
# TEST 4: No scale gives null mm fields
# ---------------------------------------------------------------------------
def test_no_scale_gives_null_mm_fields(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_scale4@test.com", "admin")
    image = setup_test_image(db_session, tmp_path, admin)

    run = AnalysisRun(image_id=image.image_id, status="done")
    db_session.add(run)
    db_session.commit()

    meas = CrackMeasurement(
        run_id=run.run_id,
        mask_path="dummy_mask.png",
        threshold=0.40,
        crack_pixels=300,
        length_px=80.0,
        avg_width_px=3.0,
        max_width_px=5.0,
        p95_width_px=4.5,
        area_px=300,
        density_percent=0.08,
        orientation_deg=0.0,
        num_components=1,
        num_branch_points=0,
        num_end_points=2,
        width_mode="edt2",
    )
    db_session.add(meas)
    db_session.commit()

    # Remeasure without scale
    res = client.post(f"/images/{image.image_id}/remeasure", headers=auth_headers(admin))
    assert res.status_code == 200
    m = res.json()["crack_measurements"][0]

    assert m["mm_per_pixel"] is None
    assert m["length_mm"] is None
    assert m["avg_width_mm"] is None
    assert m["max_width_mm"] is None
    assert m["length_mm_uncertainty"] is None
    assert m["width_mm_uncertainty"] is None
    assert m["scale_id"] is None


# ---------------------------------------------------------------------------
# TEST 5: Remeasure does NOT call any deep learning models (mocked & asserted)
# ---------------------------------------------------------------------------
def test_remeasure_does_not_call_any_model(client, db_session, tmp_path, monkeypatch):
    admin = create_user(db_session, "admin_scale5@test.com", "admin")
    image = setup_test_image(db_session, tmp_path, admin)

    run = AnalysisRun(image_id=image.image_id, status="done")
    db_session.add(run)
    db_session.commit()

    meas = CrackMeasurement(
        run_id=run.run_id,
        mask_path="dummy_mask.png",
        threshold=0.40,
        crack_pixels=400,
        length_px=120.0,
        avg_width_px=3.5,
        max_width_px=6.0,
        p95_width_px=5.0,
        area_px=400,
        density_percent=0.1,
        orientation_deg=10.0,
        num_components=1,
        num_branch_points=0,
        num_end_points=2,
        width_mode="edt2",
    )
    db_session.add(meas)
    db_session.commit()

    # Set active scale with perspective not perpendicular
    scale_payload = {
        "mm_per_pixel": 0.25,
        "camera_perpendicular": False,
    }
    client.put(f"/images/{image.image_id}/scale", json=scale_payload, headers=auth_headers(admin))

    # Mock all model inference functions
    mock_yolo = MagicMock()
    mock_seg = MagicMock()
    mock_exec = MagicMock()

    monkeypatch.setattr(analysis_service_mod, "get_yolo_model", mock_yolo)
    monkeypatch.setattr(analysis_service_mod, "get_segmentation_model", mock_seg)
    monkeypatch.setattr(analysis_service_mod, "execute_image_analysis", mock_exec)

    # Execute remeasure
    res = client.post(f"/images/{image.image_id}/remeasure", headers=auth_headers(admin))
    assert res.status_code == 200

    # Assert deep learning models were NEVER called
    mock_yolo.assert_not_called()
    mock_seg.assert_not_called()
    mock_exec.assert_not_called()

    # Verify measurement was updated
    m = res.json()["crack_measurements"][0]
    assert m["length_mm"] == round(120.0 * 0.25, 2)  # 30.0 mm
    assert m["measurement_note"] == "perspective not corrected: approximate"


# ---------------------------------------------------------------------------
# TEST 6: Permissions: an unrelated inspector gets 403 on scale & remeasure
# ---------------------------------------------------------------------------
def test_unrelated_inspector_gets_403(client, db_session, tmp_path):
    owner_insp = create_user(db_session, "owner_insp@test.com", "inspector")
    stranger_insp = create_user(db_session, "stranger_insp@test.com", "inspector")
    ce_user = create_user(db_session, "ce_user@test.com", "civil_engineer")

    image = setup_test_image(db_session, tmp_path, owner_insp)

    scale_body = {"mm_per_pixel": 0.5, "camera_perpendicular": True}

    # Stranger inspector tries PUT -> 403
    res_put = client.put(f"/images/{image.image_id}/scale", json=scale_body, headers=auth_headers(stranger_insp))
    assert res_put.status_code == 403

    # Stranger inspector tries DELETE -> 403
    res_del = client.delete(f"/images/{image.image_id}/scale", headers=auth_headers(stranger_insp))
    assert res_del.status_code == 403

    # Stranger inspector tries POST remeasure -> 403
    res_rem = client.post(f"/images/{image.image_id}/remeasure", headers=auth_headers(stranger_insp))
    assert res_rem.status_code == 403

    # Owner inspector succeeds in setting scale -> 200
    res_owner = client.put(f"/images/{image.image_id}/scale", json=scale_body, headers=auth_headers(owner_insp))
    assert res_owner.status_code == 200

    # Civil engineer succeeds in deleting scale -> 200
    res_ce = client.delete(f"/images/{image.image_id}/scale", headers=auth_headers(ce_user))
    assert res_ce.status_code == 200


# ---------------------------------------------------------------------------
# TEST 7: Replacing a scale keeps old row with is_current=False
# ---------------------------------------------------------------------------
def test_replacing_scale_keeps_old_row(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_scale7@test.com", "admin")
    image = setup_test_image(db_session, tmp_path, admin)

    # 1. Set first scale: 0.5 mm/px
    res1 = client.put(f"/images/{image.image_id}/scale", json={
        "mm_per_pixel": 0.5, "camera_perpendicular": True
    }, headers=auth_headers(admin))
    assert res1.status_code == 200

    # 2. Set second scale: 0.25 mm/px
    res2 = client.put(f"/images/{image.image_id}/scale", json={
        "mm_per_pixel": 0.25, "camera_perpendicular": False
    }, headers=auth_headers(admin))
    assert res2.status_code == 200

    # Check database rows
    scales = db_session.query(ImageScale).filter(ImageScale.image_id == image.image_id).order_by(ImageScale.scale_id.asc()).all()
    assert len(scales) == 2

    # Old row is preserved with is_current=False
    assert scales[0].is_current is False
    assert scales[0].mm_per_pixel == 0.5

    # New row is active with is_current=True
    assert scales[1].is_current is True
    assert scales[1].mm_per_pixel == 0.25
    assert scales[1].camera_perpendicular is False

    # GET returns the current active scale
    res_get = client.get(f"/images/{image.image_id}/scale", headers=auth_headers(admin))
    assert res_get.status_code == 200
    assert res_get.json()["scale_id"] == scales[1].scale_id
    assert res_get.json()["mm_per_pixel"] == 0.25

