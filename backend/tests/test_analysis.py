"""Automated pytest suite for AI Analysis Service and Endpoints.

Tests:
1. Analysis creates database rows (AnalysisRun, Detection, CrackMeasurement, run_models).
2. Failed analysis sets status='failed' with error_message without breaking uploads or crashing.
3. User without access gets 403 on analysis endpoints.
4. mm fields are None without scale, and computed when scale is provided.
5. Rejected images are skipped or rejected with 400.
6. A second configured detector produces detections with its own model_id.
"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
import pytest
import torch
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
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.user import User
from app.services.analysis_service import execute_image_analysis
from app.services.security import create_access_token, hash_password

# In-memory SQLite engine
TEST_DB_URL = "sqlite:///:memory:"
engine_test = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function")
def db_session(tmp_path, monkeypatch):
    """Isolated database session with temporary storage directories."""
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


def create_test_asset(db, name="Bridge A", asset_type="bridge") -> InfrastructureAsset:
    valid_types = ["building", "bridge", "road", "tunnel", "dam", "concrete_structure", "retaining_wall", "industrial"]
    asset = InfrastructureAsset(
        name=name,
        asset_type=asset_type if asset_type in valid_types else "bridge",
        material_type="concrete",
        address="100 Main St",
        latitude=13.0,
        longitude=80.0,
        construction_year=2020,
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


def make_mock_yolo(model_id="yolov8s_rdd2022", box_coords=(50.0, 60.0, 200.0, 220.0), conf=0.88, cls_id=0):
    mock = MagicMock()
    mock.names = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}

    mock_box = MagicMock()
    mock_box.xyxy = [torch.tensor(box_coords)]
    mock_box.conf = [torch.tensor(conf)]
    mock_box.cls = [torch.tensor(cls_id)]

    mock_res = MagicMock()
    mock_res.boxes = [mock_box]

    mock.predict.return_value = [mock_res]
    return mock


def make_mock_seg(has_crack=True):
    class MockSegModule(torch.nn.Module):
        def forward(self, x):
            # x shape: (1, 3, H, W)
            _, _, h, w = x.shape
            logits = torch.ones((1, 1, h, w)) * (-5.0)
            if has_crack:
                # Add crack stripe
                logits[:, :, 40:70, 50:55] = 5.0
            return logits

    return MockSegModule()


# ---------------------------------------------------------------------------
# TEST 1: Analysis creates database rows
# ---------------------------------------------------------------------------
def test_analysis_creates_rows(db_session, tmp_path, monkeypatch):
    # Setup asset, inspection, image
    inspector = create_user(db_session, "insp1@test.com", "inspector")
    asset = create_test_asset(db_session, "Road A", "road")

    inspection = Inspection(asset_id=asset.asset_id, inspector_id=inspector.user_id, inspection_date=date.today())
    db_session.add(inspection)
    db_session.commit()

    img_file = tmp_path / "uploads" / "test_img.jpg"
    create_dummy_image_file(img_file, 800, 600)

    image = ImageModel(
        inspection_id=inspection.inspection_id,
        uploaded_by=inspector.user_id,
        file_path=str(img_file),
        original_filename="test_img.jpg",
        file_hash="dummyhash123",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db_session.add(image)
    db_session.commit()

    # Pre-register models in DB
    db_session.add(ModelVersion(
        model_id="yolov8s_rdd2022", model_name="YOLOv8s", task="detection",
        weights_path="dummy.pt", threshold=0.25, is_active=True
    ))
    db_session.add(ModelVersion(
        model_id="unetplusplus_crack500", model_name="U-Net++", task="segmentation",
        weights_path="dummy.pth", threshold=0.40, is_active=True
    ))
    db_session.commit()

    # Mock model loaders
    monkeypatch.setattr("app.services.analysis_service.get_yolo_model", lambda p: make_mock_yolo())
    monkeypatch.setattr("app.services.analysis_service.get_segmentation_model", lambda p: make_mock_seg())

    # Create run
    run = AnalysisRun(image_id=image.image_id, status="pending")
    db_session.add(run)
    db_session.commit()

    # Execute
    res = execute_image_analysis(run.run_id, image.image_id, db_session)
    assert res.status == "done"
    assert res.seconds is not None
    assert res.image_scale_note is not None

    # Verify detections
    dets = db_session.query(Detection).filter(Detection.run_id == run.run_id).all()
    assert len(dets) == 1
    assert dets[0].model_id == "yolov8s_rdd2022"
    assert dets[0].damage_type == "D00"
    assert dets[0].confidence == pytest.approx(0.88, abs=0.01)
    assert dets[0].x_min == 50.0

    # Verify crack measurement
    meas = db_session.query(CrackMeasurement).filter(CrackMeasurement.run_id == run.run_id).first()
    assert meas is not None
    assert meas.crack_pixels > 0
    assert meas.length_px > 0
    assert meas.avg_width_px > 0
    assert meas.width_mode == "edt2"
    assert Path(meas.mask_path).name.endswith(".png")

    # Verify run_models junction
    linked = db_session.query(run_models).filter(run_models.c.run_id == run.run_id).all()
    model_ids = [row.model_id for row in linked]
    assert "yolov8s_rdd2022" in model_ids
    assert "unetplusplus_crack500" in model_ids


# ---------------------------------------------------------------------------
# TEST 2: Failed analysis sets status='failed' without breaking upload
# ---------------------------------------------------------------------------
def test_failed_analysis_sets_status_failed_without_breaking_upload(db_session, tmp_path, monkeypatch):
    inspector = create_user(db_session, "insp2@test.com", "inspector")
    asset = create_test_asset(db_session, "Road B", "road")

    inspection = Inspection(asset_id=asset.asset_id, inspector_id=inspector.user_id, inspection_date=date.today())
    db_session.add(inspection)
    db_session.commit()

    img_file = tmp_path / "uploads" / "fail_img.jpg"
    create_dummy_image_file(img_file, 800, 600)

    image = ImageModel(
        inspection_id=inspection.inspection_id,
        uploaded_by=inspector.user_id,
        file_path=str(img_file),
        original_filename="fail_img.jpg",
        file_hash="dummyhashfail",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db_session.add(image)
    db_session.commit()

    # Simulate inference failure
    def mock_broken_yolo(p):
        raise RuntimeError("Simulated inference engine out of memory error.")

    monkeypatch.setattr("app.services.analysis_service.get_yolo_model", mock_broken_yolo)

    run = AnalysisRun(image_id=image.image_id, status="pending")
    db_session.add(run)
    db_session.commit()

    res = execute_image_analysis(run.run_id, image.image_id, db_session)
    assert res.status == "failed"
    assert "Simulated inference engine" in res.error_message

    # Verify original image remains intact
    fresh_img = db_session.query(ImageModel).filter(ImageModel.image_id == image.image_id).first()
    assert fresh_img is not None
    assert fresh_img.quality_status == "passed"


# ---------------------------------------------------------------------------
# TEST 3: User without access gets 403
# ---------------------------------------------------------------------------
def test_user_without_access_gets_403(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.analysis.execute_image_analysis", MagicMock())
    admin = create_user(db_session, "admin@test.com", "admin")
    insp1 = create_user(db_session, "owner@test.com", "inspector")
    insp2 = create_user(db_session, "stranger@test.com", "inspector")

    asset = create_test_asset(db_session, "Tunnel T", "tunnel")

    inspection = Inspection(asset_id=asset.asset_id, inspector_id=insp1.user_id, inspection_date=date.today())
    db_session.add(inspection)
    db_session.commit()

    img_file = tmp_path / "uploads" / "sec_img.jpg"
    create_dummy_image_file(img_file, 800, 600)

    image = ImageModel(
        inspection_id=inspection.inspection_id,
        uploaded_by=insp1.user_id,
        file_path=str(img_file),
        original_filename="sec_img.jpg",
        file_hash="dummysec",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db_session.add(image)
    db_session.commit()

    # Stranger inspector tries to POST /images/{id}/analyze
    res = client.post(f"/images/{image.image_id}/analyze", headers=auth_headers(insp2))
    assert res.status_code == 403

    # Stranger inspector tries to POST /inspections/{id}/analyze (requires admin or civil_engineer)
    res_insp = client.post(f"/inspections/{inspection.inspection_id}/analyze", headers=auth_headers(insp2))
    assert res_insp.status_code == 403

    # Stranger inspector tries to GET /images/{id}/analysis
    res_get = client.get(f"/images/{image.image_id}/analysis", headers=auth_headers(insp2))
    assert res_get.status_code == 403

    # Owner inspector succeeds in enqueuing analysis
    res_owner = client.post(f"/images/{image.image_id}/analyze", headers=auth_headers(insp1))
    assert res_owner.status_code == 202


# ---------------------------------------------------------------------------
# TEST 4: mm fields are None without scale, and populated when scale is given
# ---------------------------------------------------------------------------
def test_mm_fields_are_none_without_scale(db_session, tmp_path, monkeypatch):
    admin = create_user(db_session, "admin_scale@test.com", "admin")
    asset = create_test_asset(db_session, "Wall W", "retaining_wall")

    inspection = Inspection(asset_id=asset.asset_id, inspector_id=admin.user_id, inspection_date=date.today())
    db_session.add(inspection)
    db_session.commit()

    img_file = tmp_path / "uploads" / "scale_img.jpg"
    create_dummy_image_file(img_file, 800, 600)

    image = ImageModel(
        inspection_id=inspection.inspection_id,
        uploaded_by=admin.user_id,
        file_path=str(img_file),
        original_filename="scale_img.jpg",
        file_hash="dummyscale",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db_session.add(image)
    db_session.commit()

    monkeypatch.setattr("app.services.analysis_service.get_yolo_model", lambda p: make_mock_yolo())
    monkeypatch.setattr("app.services.analysis_service.get_segmentation_model", lambda p: make_mock_seg())

    # Case A: mm_per_pixel is None
    run_no_scale = AnalysisRun(image_id=image.image_id, status="pending")
    db_session.add(run_no_scale)
    db_session.commit()

    execute_image_analysis(run_no_scale.run_id, image.image_id, db_session, mm_per_pixel=None)
    meas_a = db_session.query(CrackMeasurement).filter(CrackMeasurement.run_id == run_no_scale.run_id).first()
    assert meas_a.mm_per_pixel is None
    assert meas_a.length_mm is None
    assert meas_a.avg_width_mm is None
    assert meas_a.max_width_mm is None

    # Case B: mm_per_pixel is provided (e.g. 0.5 mm/px)
    run_scale = AnalysisRun(image_id=image.image_id, status="pending")
    db_session.add(run_scale)
    db_session.commit()

    execute_image_analysis(run_scale.run_id, image.image_id, db_session, mm_per_pixel=0.5)
    meas_b = db_session.query(CrackMeasurement).filter(CrackMeasurement.run_id == run_scale.run_id).first()
    assert meas_b.mm_per_pixel == 0.5
    assert meas_b.length_mm is not None
    assert meas_b.length_mm > 0.0
    assert meas_b.avg_width_mm is not None


# ---------------------------------------------------------------------------
# TEST 5: Rejected images are skipped or refused
# ---------------------------------------------------------------------------
def test_rejected_images_are_skipped(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_rej@test.com", "admin")
    asset = create_test_asset(db_session, "Dam D", "dam")

    inspection = Inspection(asset_id=asset.asset_id, inspector_id=admin.user_id, inspection_date=date.today())
    db_session.add(inspection)
    db_session.commit()

    img_file = tmp_path / "uploads" / "rej_img.jpg"
    create_dummy_image_file(img_file, 800, 600)

    image = ImageModel(
        inspection_id=inspection.inspection_id,
        uploaded_by=admin.user_id,
        file_path=str(img_file),
        original_filename="rej_img.jpg",
        file_hash="dummyrej",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="rejected",
    )
    db_session.add(image)
    db_session.commit()

    # Direct analyze on rejected image must return 400 Bad Request
    res = client.post(f"/images/{image.image_id}/analyze", headers=auth_headers(admin))
    assert res.status_code == 400
    assert "rejected" in res.json()["detail"]

    # Inspection batch analyze must skip rejected images
    res_batch = client.post(f"/inspections/{inspection.inspection_id}/analyze", headers=auth_headers(admin))
    assert res_batch.status_code == 400  # No valid images to analyze


# ---------------------------------------------------------------------------
# TEST 6: Second configured detector produces detections with its own model_id
# ---------------------------------------------------------------------------
def test_second_configured_detector_produces_detections_with_its_own_model_id(db_session, tmp_path, monkeypatch):
    admin = create_user(db_session, "admin_multi@test.com", "admin")
    asset = create_test_asset(db_session, "Culvert C", "tunnel")

    inspection = Inspection(asset_id=asset.asset_id, inspector_id=admin.user_id, inspection_date=date.today())
    db_session.add(inspection)
    db_session.commit()

    img_file = tmp_path / "uploads" / "multi_img.jpg"
    create_dummy_image_file(img_file, 800, 600)

    image = ImageModel(
        inspection_id=inspection.inspection_id,
        uploaded_by=admin.user_id,
        file_path=str(img_file),
        original_filename="multi_img.jpg",
        file_hash="dummymulti",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db_session.add(image)
    db_session.commit()

    # Configure TWO detectors
    detector_list = [
        {
            "model_id": "yolov8s_rdd2022",
            "model_name": "YOLOv8s RDD2022",
            "weights_path": "dummy_yolo.pt",
            "class_names": {0: "longitudinal crack"},
            "confidence": 0.25,
        },
        {
            "model_id": "spalling_detector_v1",
            "model_name": "Spalling / Corrosion Detector",
            "weights_path": "dummy_spall.pt",
            "class_names": {0: "spalling corrosion"},
            "confidence": 0.30,
        },
    ]
    monkeypatch.setattr(settings, "DETECTION_MODELS_CONFIG", detector_list)

    # Mock YOLO loader to return different detections per model
    def mock_get_yolo_multi(weights_path):
        if "spall" in weights_path:
            return make_mock_yolo(model_id="spalling_detector_v1", box_coords=(300.0, 300.0, 450.0, 450.0), conf=0.92, cls_id=0)
        return make_mock_yolo(model_id="yolov8s_rdd2022", box_coords=(50.0, 50.0, 150.0, 150.0), conf=0.85, cls_id=0)

    monkeypatch.setattr("app.services.analysis_service.get_yolo_model", mock_get_yolo_multi)
    monkeypatch.setattr("app.services.analysis_service.get_segmentation_model", lambda p: make_mock_seg())

    run = AnalysisRun(image_id=image.image_id, status="pending")
    db_session.add(run)
    db_session.commit()

    res = execute_image_analysis(run.run_id, image.image_id, db_session)
    assert res.status == "done"

    detections = db_session.query(Detection).filter(Detection.run_id == run.run_id).all()
    assert len(detections) == 2

    model_ids = {d.model_id for d in detections}
    assert "yolov8s_rdd2022" in model_ids
    assert "spalling_detector_v1" in model_ids

    # Check distinct damage labels
    labels = {d.damage_label for d in detections}
    assert "longitudinal crack" in labels
    assert "spalling corrosion" in labels


# ---------------------------------------------------------------------------
# MILESTONE 3 STEP 4 TESTS: Multi-Detector Runner, Asset Type Routing, RBAC
# ---------------------------------------------------------------------------

def make_mock_rtdetr(box_coords=(120.0, 150.0, 300.0, 350.0), conf=0.78, cls_id=1):
    mock = MagicMock()
    mock.names = {0: "crack", 1: "spallation", 2: "exposed_bars", 3: "efflorescence", 4: "corrosion_stain"}
    mock_box = MagicMock()
    mock_box.xyxy = [torch.tensor(box_coords)]
    mock_box.conf = [torch.tensor(conf)]
    mock_box.cls = [torch.tensor(cls_id)]
    mock_res = MagicMock()
    mock_res.boxes = [mock_box]
    mock.predict.return_value = [mock_res]
    return mock


def test_detector_selection_by_asset_type(db_session, tmp_path, monkeypatch):
    """Verify detector selection by asset type (road -> road detector, bridge -> CODEBRIM, unknown/RUN_ALL -> both)."""
    inspector = create_user(db_session, "sel_insp@test.com", "inspector")

    img_file = tmp_path / "uploads" / "sel_test.jpg"
    create_dummy_image_file(img_file, 800, 600)

    # 1. Road asset -> Should run road detector only
    road_asset = create_test_asset(db_session, name="Highway 1", asset_type="road")
    road_insp = Inspection(asset_id=road_asset.asset_id, inspector_id=inspector.user_id, inspection_date=date.today())
    db_session.add(road_insp)
    db_session.commit()
    road_img = ImageModel(
        inspection_id=road_insp.inspection_id,
        uploaded_by=inspector.user_id,
        file_path=str(img_file),
        original_filename="sel_test.jpg",
        file_hash="hash_road_1",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db_session.add(road_img)
    db_session.commit()

    called_detectors = []
    def mock_yolo_call(p):
        called_detectors.append("yolov8s_rdd2022")
        return make_mock_yolo()
    def mock_rtdetr_call(p):
        called_detectors.append("A2_rtdetr_l")
        return make_mock_rtdetr()

    monkeypatch.setattr("app.services.analysis_service.get_yolo_model", mock_yolo_call)
    monkeypatch.setattr("app.services.analysis_service.get_rtdetr_model", mock_rtdetr_call)
    monkeypatch.setattr("app.services.analysis_service.get_segmentation_model", lambda p: make_mock_seg())
    monkeypatch.setattr(settings, "RUN_ALL_DETECTORS", False)

    run_road = AnalysisRun(image_id=road_img.image_id, status="pending")
    db_session.add(run_road)
    db_session.commit()

    res_road = execute_image_analysis(run_road.run_id, road_img.image_id, db_session)
    assert res_road.status == "done"
    assert "yolov8s_rdd2022" in called_detectors
    assert "A2_rtdetr_l" not in called_detectors

    # 2. Bridge asset -> Should run CODEBRIM detector only
    called_detectors.clear()
    bridge_asset = create_test_asset(db_session, name="Overpass 5", asset_type="bridge")
    bridge_insp = Inspection(asset_id=bridge_asset.asset_id, inspector_id=inspector.user_id, inspection_date=date.today())
    db_session.add(bridge_insp)
    db_session.commit()
    bridge_img = ImageModel(
        inspection_id=bridge_insp.inspection_id,
        uploaded_by=inspector.user_id,
        file_path=str(img_file),
        original_filename="sel_test.jpg",
        file_hash="hash_bridge_1",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db_session.add(bridge_img)
    db_session.commit()

    run_bridge = AnalysisRun(image_id=bridge_img.image_id, status="pending")
    db_session.add(run_bridge)
    db_session.commit()

    res_bridge = execute_image_analysis(run_bridge.run_id, bridge_img.image_id, db_session)
    assert res_bridge.status == "done"
    assert "A2_rtdetr_l" in called_detectors
    assert "yolov8s_rdd2022" not in called_detectors

    # 3. RUN_ALL_DETECTORS=True -> Runs both detectors
    called_detectors.clear()
    monkeypatch.setattr(settings, "RUN_ALL_DETECTORS", True)
    run_all = AnalysisRun(image_id=road_img.image_id, status="pending")
    db_session.add(run_all)
    db_session.commit()

    res_all = execute_image_analysis(run_all.run_id, road_img.image_id, db_session)
    assert res_all.status == "done"
    assert "yolov8s_rdd2022" in called_detectors
    assert "A2_rtdetr_l" in called_detectors


def test_detector_override_rbac(client, db_session, tmp_path):
    """Verify that detector override list works only for admin and civil_engineer, rejecting inspectors with 403."""
    admin = create_user(db_session, "admin_ovr@test.com", "admin")
    ce = create_user(db_session, "ce_ovr@test.com", "civil_engineer")
    inspector = create_user(db_session, "insp_ovr@test.com", "inspector")

    asset = create_test_asset(db_session, "Road Ovr", "road")
    insp = Inspection(asset_id=asset.asset_id, inspector_id=inspector.user_id, inspection_date=date.today())
    db_session.add(insp)
    db_session.commit()

    img_file = tmp_path / "uploads" / "ovr.jpg"
    create_dummy_image_file(img_file)
    image = ImageModel(
        inspection_id=insp.inspection_id,
        uploaded_by=inspector.user_id,
        file_path=str(img_file),
        original_filename="ovr.jpg",
        file_hash="hash_ovr_1",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db_session.add(image)
    db_session.commit()

    # 1. Admin specifying detector override -> 202
    resp_admin = client.post(
        f"/images/{image.image_id}/analyze",
        headers=auth_headers(admin),
        json={"detectors": ["A2_rtdetr_l"]},
    )
    assert resp_admin.status_code == 202

    # 2. Civil Engineer specifying detector override -> 202
    resp_ce = client.post(
        f"/images/{image.image_id}/analyze",
        headers=auth_headers(ce),
        json={"detectors": ["yolov8s_rdd2022", "A2_rtdetr_l"]},
    )
    assert resp_ce.status_code == 202

    # 3. Inspector specifying detector override -> 403 Forbidden
    resp_insp = client.post(
        f"/images/{image.image_id}/analyze",
        headers=auth_headers(inspector),
        json={"detectors": ["A2_rtdetr_l"]},
    )
    assert resp_insp.status_code == 403
    assert "Only admin or civil_engineer can specify detector overrides" in resp_insp.json()["detail"]


def test_missing_weights_file_skips_and_finishes_with_warning(db_session, tmp_path, monkeypatch):
    """Verify that a missing weights file skips that detector, records a warning, and completes analysis."""
    inspector = create_user(db_session, "skip_insp@test.com", "inspector")
    asset = create_test_asset(db_session, "Unknown Asset", "bridge")
    insp = Inspection(asset_id=asset.asset_id, inspector_id=inspector.user_id, inspection_date=date.today())
    db_session.add(insp)
    db_session.commit()

    img_file = tmp_path / "uploads" / "skip_test.jpg"
    create_dummy_image_file(img_file)
    image = ImageModel(
        inspection_id=insp.inspection_id,
        uploaded_by=inspector.user_id,
        file_path=str(img_file),
        original_filename="skip_test.jpg",
        file_hash="hash_skip_1",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db_session.add(image)
    db_session.commit()

    # Configure RUN_ALL_DETECTORS so both are scheduled
    monkeypatch.setattr(settings, "RUN_ALL_DETECTORS", True)

    # Road detector works fine
    monkeypatch.setattr("app.services.analysis_service.get_yolo_model", lambda p: make_mock_yolo())
    # CODEBRIM fails with missing weights
    def mock_broken_rtdetr(p):
        raise FileNotFoundError(f"Weights file not found: {p}")
    monkeypatch.setattr("app.services.analysis_service.get_rtdetr_model", mock_broken_rtdetr)
    monkeypatch.setattr("app.services.analysis_service.get_segmentation_model", lambda p: make_mock_seg())

    run = AnalysisRun(image_id=image.image_id, status="pending")
    db_session.add(run)
    db_session.commit()

    res = execute_image_analysis(run.run_id, image.image_id, db_session)
    assert res.status == "done"
    assert res.error_message is not None
    assert "skipped" in res.error_message.lower()

    # Detections from the successful road detector are still recorded
    dets = db_session.query(Detection).filter(Detection.run_id == run.run_id).all()
    assert len(dets) >= 1
    assert dets[0].model_id == "yolov8s_rdd2022"


def test_detections_carry_correct_model_id_and_class_names(db_session, tmp_path, monkeypatch):
    """Verify that detections carry the correct model_id and class names."""
    inspector = create_user(db_session, "classes_insp@test.com", "inspector")
    asset = create_test_asset(db_session, "Bridge Classes", "bridge")
    insp = Inspection(asset_id=asset.asset_id, inspector_id=inspector.user_id, inspection_date=date.today())
    db_session.add(insp)
    db_session.commit()

    img_file = tmp_path / "uploads" / "classes_test.jpg"
    create_dummy_image_file(img_file)
    image = ImageModel(
        inspection_id=insp.inspection_id,
        uploaded_by=inspector.user_id,
        file_path=str(img_file),
        original_filename="classes_test.jpg",
        file_hash="hash_classes_1",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        quality_status="passed",
    )
    db_session.add(image)
    db_session.commit()

    # Run CODEBRIM producing class 1 (spallation)
    monkeypatch.setattr("app.services.analysis_service.get_rtdetr_model", lambda p: make_mock_rtdetr(cls_id=1, conf=0.82))
    monkeypatch.setattr("app.services.analysis_service.get_segmentation_model", lambda p: make_mock_seg())

    run = AnalysisRun(image_id=image.image_id, status="pending")
    db_session.add(run)
    db_session.commit()

    res = execute_image_analysis(run.run_id, image.image_id, db_session)
    assert res.status == "done"

    dets = db_session.query(Detection).filter(Detection.run_id == run.run_id).all()
    assert len(dets) == 1
    assert dets[0].model_id == "A2_rtdetr_l"
    assert dets[0].damage_type == "spallation"
    assert dets[0].damage_label == "spallation"
    assert dets[0].confidence == pytest.approx(0.82, abs=0.01)


def test_get_models_endpoint_returns_both_detectors(client, db_session):
    """Verify GET /models returns registered detectors with required metadata."""
    inspector = create_user(db_session, "models_user@test.com", "inspector")

    resp = client.get("/models", headers=auth_headers(inspector))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    model_names = [d["name"] for d in data]
    assert "yolov8s_rdd2022" in model_names
    assert "A2_rtdetr_l" in model_names

    codebrim_entry = next(d for d in data if d["name"] == "A2_rtdetr_l")
    assert codebrim_entry["imgsz"] == 960
    assert codebrim_entry["conf"] == pytest.approx(0.563, abs=0.01)
    assert "bridge" in codebrim_entry["applicable_asset_types"]
    assert "CODEBRIM" in codebrim_entry["domain_note"]
    assert "crack" in codebrim_entry["classes"]
    assert "spallation" in codebrim_entry["classes"]
    assert "exposed_bars" in codebrim_entry["classes"]
    assert "efflorescence" in codebrim_entry["classes"]
    assert "corrosion_stain" in codebrim_entry["classes"]

    road_entry = next(d for d in data if d["name"] == "yolov8s_rdd2022")
    assert road_entry["imgsz"] == 640
    assert "road" in road_entry["applicable_asset_types"]
    assert "RDD2022" in road_entry["domain_note"]
