"""Pytest suite for Advisory Damage Severity Assessment (Milestone 3, Step 3).

Verifies:
1. More density never lowers severity (monotonicity).
2. No scale means 0 mm points and a "width not scored: no scale" note.
3. Empty results return 'none' with the exact disclaimer note.
4. exposed_bars with confidence >= 0.5 forces at least 'severe'.
5. Asset importance 'high' raises priority suggestion by one level.
6. Unknown class names receive the default 10 points and an explanation warning.
7. Result is deterministic and factors list sums to score before cap.
8. Corrupted rules files (gaps, overlaps, negative weights) are rejected with ValueError.
9. Inspectors receive 403 Forbidden on the review endpoint.
10. Review and corrections preserve history and audit log.
11. Assessment failure does not fail the analysis pipeline.
12. Recomputation creates a new assessment while keeping the old row marked is_superseded=True.
"""

from datetime import date
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.analysis import AnalysisRun, CrackMeasurement, Detection
from app.models.asset import InfrastructureAsset
from app.models.audit_log import AuditLog
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.severity import InspectionSeverity, SeverityAssessment
from app.models.user import User
from app.services.security import create_access_token, hash_password
from app.services.severity_service import (
    SEVERITY_ORDER,
    SEVERITY_RANK,
    assess,
    assess_and_save_run,
    load_severity_rules,
    update_inspection_severity,
)

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
    monkeypatch.setattr("app.routers.severity.get_db", override_get_db)
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


def create_test_asset(db, importance_level="medium") -> InfrastructureAsset:
    asset = InfrastructureAsset(
        name="Test Bridge Severity",
        asset_type="bridge",
        material_type="concrete",
        address="100 Main St",
        latitude=34.0,
        longitude=-118.0,
        construction_year=2000,
        responsible_department="Civil Engineering",
        inspection_frequency_days=180,
        importance_level=importance_level,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def create_test_hierarchy(db, importance_level="medium"):
    admin = create_user(db, "admin_sev@test.com", "admin")
    ce = create_user(db, "ce_sev@test.com", "civil_engineer")
    inspector = create_user(db, "insp_sev@test.com", "inspector")
    other_insp = create_user(db, "other_insp@test.com", "inspector")

    asset = create_test_asset(db, importance_level=importance_level)
    inspection = Inspection(
        asset_id=asset.asset_id,
        inspector_id=inspector.user_id,
        inspection_date=date.today(),
        status="in_progress",
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    image = ImageModel(
        inspection_id=inspection.inspection_id,
        uploaded_by=inspector.user_id,
        original_filename="severity_test.jpg",
        file_path="uploads/severity_test.jpg",
        file_hash="hash_severity_12345",
        file_size_bytes=1000,
        width_px=1000,
        height_px=1000,
        quality_status="passed",
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return admin, ce, inspector, other_insp, asset, inspection, image


# ---------------------------------------------------------------------------
# 1. Monotonicity: More density never lowers severity
# ---------------------------------------------------------------------------
def test_more_density_never_lowers_severity():
    densities = [0.1, 0.4, 0.5, 1.5, 2.0, 3.5, 5.0, 8.0, 10.0, 15.0, 25.0]
    prev_score = -1.0
    prev_rank = -1

    for d in densities:
        measurement = {
            "crack_pixels": int(d * 1000),
            "density_percent": d,
            "length_px": 200.0,
            "avg_width_px": 5.0,
            "max_width_px": 10.0,
            "num_components": 1,
            "num_branch_points": 0,
        }
        res = assess(measurement=measurement, detections=[], image_size=(1000, 1000))
        curr_score = res["score"]
        curr_rank = SEVERITY_RANK[res["severity_level"]]

        assert curr_score >= prev_score, f"Score decreased from {prev_score} to {curr_score} at density {d}"
        assert curr_rank >= prev_rank, f"Severity rank decreased from {prev_rank} to {curr_rank} at density {d}"

        prev_score = curr_score
        prev_rank = curr_rank


# ---------------------------------------------------------------------------
# 2. No scale means no mm points and "width not scored: no scale" note
# ---------------------------------------------------------------------------
def test_no_scale_means_no_mm_points_and_note():
    measurement = {
        "crack_pixels": 5000,
        "density_percent": 3.0,
        "length_px": 300.0,
        "avg_width_px": 6.0,
        "max_width_px": 12.0,
        "num_components": 1,
        "num_branch_points": 0,
        "scale_id": None,
        "mm_per_pixel": None,
        "max_width_mm": None,
    }
    res = assess(measurement=measurement, detections=[], image_size=(1000, 1000))

    width_factor = next(f for f in res["factors"] if f["factor"] == "width_mm")
    assert width_factor["points"] == 0.0
    assert "width not scored: no scale" in width_factor["note"]
    assert "12.0px" in width_factor["note"]  # pixel values must not be hidden


# ---------------------------------------------------------------------------
# 3. Empty results give 'none' and required disclaimer note
# ---------------------------------------------------------------------------
def test_empty_results_give_none_and_disclaimer():
    res = assess(measurement=None, detections=[], image_size=(1000, 1000))
    assert res["severity_level"] == "none"
    assert res["score"] == 0.0
    expected_note = "no damage detected by the AI; this is not evidence that there is no damage"
    assert expected_note in res["warnings"]


# ---------------------------------------------------------------------------
# 4. exposed_bars forces at least severe
# ---------------------------------------------------------------------------
def test_exposed_bars_forces_at_least_severe():
    # Measurement with minimal damage that would normally be 'none' or 'minor'
    measurement = {
        "crack_pixels": 200,
        "density_percent": 0.1,
        "length_px": 50.0,
        "avg_width_px": 2.0,
        "max_width_px": 3.0,
        "num_components": 1,
        "num_branch_points": 0,
    }
    # Detection of exposed_bars with confidence 0.6 >= 0.5
    detections = [
        {
            "damage_type": "exposed_bars",
            "damage_label": "exposed_bars",
            "confidence": 0.60,
            "x_min": 100,
            "y_min": 100,
            "x_max": 200,
            "y_max": 200,
        }
    ]
    res = assess(measurement=measurement, detections=detections, image_size=(1000, 1000))
    # Even if total score is under 55, forced minimum requires at least severe
    assert SEVERITY_RANK[res["severity_level"]] >= SEVERITY_RANK["severe"]


# ---------------------------------------------------------------------------
# 5. Asset importance high raises priority one level
# ---------------------------------------------------------------------------
def test_asset_importance_high_raises_priority_one_level():
    measurement = {
        "crack_pixels": 2000,
        "density_percent": 1.0,  # factor a: 10 pts -> 'minor'
        "length_px": 50.0,
        "avg_width_px": 2.0,
        "max_width_px": 4.0,
        "num_components": 1,
        "num_branch_points": 0,
    }

    # Medium importance asset
    asset_med = {"importance_level": "medium"}
    res_med = assess(measurement=measurement, detections=[], image_size=(1000, 1000), asset=asset_med)
    assert res_med["severity_level"] == "minor"
    assert res_med["priority_suggestion"] == "low"

    # High importance asset
    asset_high = {"importance_level": "high"}
    res_high = assess(measurement=measurement, detections=[], image_size=(1000, 1000), asset=asset_high)
    assert res_high["severity_level"] == "minor"
    assert res_high["priority_suggestion"] == "medium"  # elevated from low -> medium


# ---------------------------------------------------------------------------
# 6. Unknown class gets default 10 and a warning
# ---------------------------------------------------------------------------
def test_unknown_class_gets_default_and_warning():
    detections = [
        {
            "damage_type": "unidentified_extrusion",
            "damage_label": "unidentified_extrusion",
            "confidence": 0.85,
            "x_min": 10,
            "y_min": 10,
            "x_max": 50,
            "y_max": 50,
        }
    ]
    res = assess(measurement=None, detections=detections, image_size=(1000, 1000))
    dt_factor = next(f for f in res["factors"] if f["factor"] == "damage_type")
    assert dt_factor["points"] == 10.0
    assert any("unidentified_extrusion" in w and "10" in w for w in res["warnings"])


# ---------------------------------------------------------------------------
# 7. Result is deterministic and factors sum to score before cap
# ---------------------------------------------------------------------------
def test_result_deterministic_and_factors_sum_to_score():
    measurement = {
        "crack_pixels": 8000,
        "density_percent": 8.0,  # 30 pts
        "length_px": 800.0,      # diagonal ~1414, rel_len ~0.565 -> 10 pts
        "avg_width_px": 10.0,
        "max_width_px": 20.0,
        "num_components": 4,     # +2 comp bonus
        "num_branch_points": 5,  # rate = 5/800*1000 = 6.25 -> 6 pts -> capped at 8
        "scale_id": 1,
        "mm_per_pixel": 0.5,
        "max_width_mm": 4.0,     # 15 pts
        "width_mm_uncertainty": 0.2,
    }
    detections = [
        {
            "damage_type": "D40",
            "damage_label": "pothole",
            "confidence": 0.70,
            "x_min": 100,
            "y_min": 100,
            "x_max": 300,
            "y_max": 300,        # area = 40000 / 1000000 = 0.04 -> share >= 0.02 -> 5 pts
        }
    ]
    res1 = assess(measurement=measurement, detections=detections, image_size=(1000, 1000))
    res2 = assess(measurement=measurement, detections=detections, image_size=(1000, 1000))

    assert res1 == res2, "Severity assessment must be strictly deterministic."

    # Sum of factor points must equal raw_score before cap
    factor_sum = sum(f["points"] for f in res1["factors"])
    assert round(factor_sum, 2) == round(res1["raw_score"], 2)
    assert res1["score"] == min(100.0, res1["raw_score"])


# ---------------------------------------------------------------------------
# 8. Corrupted rules file is rejected with ValueError
# ---------------------------------------------------------------------------
def test_corrupted_rules_file_rejected(tmp_path):
    # Missing required field
    corrupt_file = tmp_path / "corrupt_rules.json"
    corrupt_file.write_text(json.dumps({"invalid": "data"}), encoding="utf-8")

    with pytest.raises(ValueError, match="rules_version"):
        load_severity_rules(corrupt_file)

    # Gap in bands (0-10, then 15-100)
    gap_file = tmp_path / "gap_rules.json"
    gap_data = {
        "rules_version": "1.0.0",
        "status": "test",
        "bands": [
            {"min_score": 0.0, "max_score": 10.0, "severity": "none"},
            {"min_score": 15.0, "max_score": 100.0, "severity": "critical"},
        ],
        "factors": {},
    }
    gap_file.write_text(json.dumps(gap_data), encoding="utf-8")
    with pytest.raises(ValueError, match="Gap or overlap"):
        load_severity_rules(gap_file)

    # Negative points
    neg_file = tmp_path / "neg_rules.json"
    neg_data = {
        "rules_version": "1.0.0",
        "status": "test",
        "bands": [
            {"min_score": 0.0, "max_score": 100.0, "severity": "critical"},
        ],
        "factors": {
            "crack_density_percent": {
                "thresholds": [{"max": 1.0, "points": -5.0}]
            }
        },
    }
    neg_file.write_text(json.dumps(neg_data), encoding="utf-8")
    with pytest.raises(ValueError, match="Negative points"):
        load_severity_rules(neg_file)


# ---------------------------------------------------------------------------
# 9. Inspector gets 403 on review endpoint
# ---------------------------------------------------------------------------
def test_inspector_gets_403_on_review(client, db_session):
    admin, ce, inspector, other_insp, asset, inspection, image = create_test_hierarchy(db_session)

    run = AnalysisRun(image_id=image.image_id, status="done")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    assessment = assess_and_save_run(run_id=run.run_id, db=db_session)
    assert assessment is not None

    payload = {"action": "confirm", "comment": "Inspector attempt"}
    resp = client.put(
        f"/severity/{assessment.assessment_id}/review",
        json=payload,
        headers=auth_header(inspector),
    )
    assert resp.status_code == 403
    assert "Only civil engineers and administrators" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 10. Correction keeps history and creates audit log
# ---------------------------------------------------------------------------
def test_correction_keeps_history_and_audit_log(client, db_session):
    admin, ce, inspector, other_insp, asset, inspection, image = create_test_hierarchy(db_session)

    run = AnalysisRun(image_id=image.image_id, status="done")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    assessment = assess_and_save_run(run_id=run.run_id, db=db_session)

    payload = {
        "action": "correct",
        "final_severity": "severe",
        "comment": "Field inspection confirmed severe subsurface delamination.",
    }
    resp = client.put(
        f"/severity/{assessment.assessment_id}/review",
        json=payload,
        headers=auth_header(ce),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["review_status"] == "corrected"
    assert data["final_severity"] == "severe"
    assert data["review_comment"] == payload["comment"]

    # Verify audit log entry exists with details
    logs = db_session.query(AuditLog).filter(AuditLog.entity_type == "severity_assessment").all()
    assert len(logs) >= 1
    log_action = logs[-1].action
    assert "severity_correct" in log_action
    assert "severe" in log_action
    assert payload["comment"] in log_action


# ---------------------------------------------------------------------------
# 11. Assessment failure does not fail the analysis pipeline
# ---------------------------------------------------------------------------
def test_assessment_failure_does_not_fail_analysis(monkeypatch, db_session, tmp_path):
    from app.services.analysis_service import execute_image_analysis
    from app.models.analysis import ModelVersion
    import torch

    admin, ce, inspector, other_insp, asset, inspection, image = create_test_hierarchy(db_session)

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

    # Mock YOLO
    mock_yolo = MagicMock()
    mock_yolo.names = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}
    mock_box = MagicMock()
    mock_box.xyxy = [torch.tensor([10.0, 10.0, 50.0, 50.0])]
    mock_box.conf = [torch.tensor(0.88)]
    mock_box.cls = [torch.tensor(0)]
    mock_res = MagicMock()
    mock_res.boxes = [mock_box]
    mock_yolo.predict.return_value = [mock_res]
    monkeypatch.setattr("app.services.analysis_service.get_yolo_model", lambda p: mock_yolo)

    # Mock Segmentation
    class MockSegModule(torch.nn.Module):
        def forward(self, x):
            _, _, h, w = x.shape
            logits = torch.ones((1, 1, h, w)) * (-5.0)
            logits[:, :, 40:70, 50:55] = 5.0
            return logits

    monkeypatch.setattr("app.services.analysis_service.get_segmentation_model", lambda p: MockSegModule())

    # Force assess_and_save_run to raise an exception
    def failing_hook(*args, **kwargs):
        raise RuntimeError("Simulated severity service network or rules failure")

    monkeypatch.setattr("app.services.severity_service.assess_and_save_run", failing_hook)

    # Create dummy image file on disk and set file_path
    img_path = tmp_path / "uploads" / "severity_test.jpg"
    pil_img = Image.new("RGB", (200, 200), color=(128, 128, 128))
    pil_img.save(str(img_path))
    image.file_path = str(img_path)
    db_session.commit()

    run = AnalysisRun(image_id=image.image_id, status="pending")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    # Run analysis
    res_run = execute_image_analysis(run_id=run.run_id, image_id=image.image_id, db=db_session)
    # Analysis must succeed despite the severity hook failure!
    assert res_run.status == "done"


# ---------------------------------------------------------------------------
# 12. Recompute marks previous assessment as is_superseded=True
# ---------------------------------------------------------------------------
def test_recompute_keeps_old_row(client, db_session):
    admin, ce, inspector, other_insp, asset, inspection, image = create_test_hierarchy(db_session)

    run = AnalysisRun(image_id=image.image_id, status="done")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    meas = CrackMeasurement(
        run_id=run.run_id,
        mask_path="masks/test.png",
        crack_pixels=5000,
        density_percent=4.0,
        length_px=400.0,
        avg_width_px=8.0,
        max_width_px=15.0,
    )
    db_session.add(meas)
    db_session.commit()

    # Initial assessment
    old_assessment = assess_and_save_run(run_id=run.run_id, db=db_session)
    assert old_assessment.is_superseded is False
    old_id = old_assessment.assessment_id

    # Call recompute endpoint as CE
    resp = client.post(
        f"/images/{image.image_id}/severity/recompute",
        headers=auth_header(ce),
    )
    assert resp.status_code == 200
    new_data = resp.json()
    new_id = new_data["assessment_id"]

    assert new_id != old_id

    # Verify both records exist in DB
    all_assessments = (
        db_session.query(SeverityAssessment)
        .filter(SeverityAssessment.image_id == image.image_id)
        .order_by(SeverityAssessment.assessment_id.asc())
        .all()
    )
    assert len(all_assessments) == 2

    # Old row is preserved and marked is_superseded=True
    assert all_assessments[0].assessment_id == old_id
    assert all_assessments[0].is_superseded is True

    # New row is active (is_superseded=False)
    assert all_assessments[1].assessment_id == new_id
    assert all_assessments[1].is_superseded is False


def test_double_crack_does_not_double_count():
    """Verify that multiple detectors reporting 'crack' take the max over detections without double-counting points."""
    measurement = {
        "crack_pixels": 2500,
        "density_percent": 1.2,
        "length_px": 200.0,
        "avg_width_px": 3.0,
        "max_width_px": 8.0,
        "num_components": 1,
        "num_branch_points": 1,
    }
    image_size = (1000, 1000)

    # Case 1: Single crack detection (e.g. from road detector)
    single_crack_det = [
        {"damage_type": "crack", "damage_label": "crack", "confidence": 0.85, "x_min": 10, "y_min": 10, "x_max": 100, "y_max": 100}
    ]
    res1 = assess(measurement=measurement, detections=single_crack_det, image_size=image_size)

    # Case 2: Double crack detection (e.g. both road detector and CODEBRIM detector report crack)
    double_crack_dets = [
        {"damage_type": "crack", "damage_label": "D00 longitudinal crack", "confidence": 0.85, "x_min": 10, "y_min": 10, "x_max": 100, "y_max": 100},
        {"damage_type": "crack", "damage_label": "crack", "confidence": 0.80, "x_min": 12, "y_min": 11, "x_max": 98, "y_max": 102},
    ]
    res2 = assess(measurement=measurement, detections=double_crack_dets, image_size=image_size)

    # Extract damage_type factor points
    factor1 = next(f for f in res1["factors"] if f["factor"] == "damage_type")
    factor2 = next(f for f in res2["factors"] if f["factor"] == "damage_type")

    assert factor1["points"] == 10.0
    assert factor2["points"] == 10.0
    assert res1["score"] == res2["score"]
    assert res1["raw_score"] == res2["raw_score"]
    assert res1["severity_level"] == res2["severity_level"]
