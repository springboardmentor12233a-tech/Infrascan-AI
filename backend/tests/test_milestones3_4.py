import datetime
import json
import sys
import uuid
from pathlib import Path
import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient

# Ensure sys.path includes backend and root
backend_dir = Path(__file__).resolve().parents[1]
root_dir = Path(__file__).resolve().parents[2]
for p in (str(backend_dir), str(root_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app
from app.db import SessionLocal
from app.models.user import User
from app.models.asset import InfrastructureAsset
from app.models.inspection import Inspection
from app.models.image import Image as ImageModel
from app.ai.geometry import extract_crack_geometry
from app.ai.severity import assess_damage_severity
from app.ai.explainability import generate_gradcam_heatmap
from app.ai.damage_detection import detect_surface_defects
from app.ai.progression import analyze_damage_progression
from app.ai.maintenance import prioritize_maintenance
from app.services.report_service import (
    generate_inspection_pdf,
    generate_inspection_csv,
    generate_inspection_json,
)
from app.services.notification_service import create_notification, get_user_notifications

client = TestClient(app)


def test_ai_geometry_extraction():
    """Verify crack geometry extraction: length, max width, density, and orientation."""
    mask = np.zeros((200, 200), dtype=np.uint8)
    # Draw a diagonal synthetic crack 4px wide
    cv2.line(mask, (30, 30), (170, 170), 255, thickness=4)

    geom = extract_crack_geometry(mask, scale_mm_per_px=0.2)
    assert geom["crack_detected"] is True
    assert geom["length_px"] > 50
    assert geom["max_width_px"] >= 3
    assert geom["avg_width_px"] >= 1
    assert geom["crack_density_pct"] > 0
    assert geom["length_mm"] is not None
    assert geom["max_width_mm"] is not None
    assert 0.0 <= geom["orientation_degrees"] <= 180.0


def test_ai_damage_severity_scoring():
    """Verify 0-100 severity scoring and category assignment."""
    # Test minor crack
    minor = assess_damage_severity(
        defect_type="diagonal_crack",
        max_width_px=2.0,
        length_px=40.0,
        crack_density_pct=0.5,
        max_width_mm=0.4,
        length_mm=8.0,
        importance_level="low",
    )
    assert minor["severity_category"] in ["no_damage", "minor", "moderate"]
    assert 0 <= minor["severity_score"] <= 100

    # Test severe/critical structural damage
    critical = assess_damage_severity(
        defect_type="concrete_spalling",
        max_width_px=35.0,
        length_px=280.0,
        crack_density_pct=15.0,
        max_width_mm=7.0,
        length_mm=56.0,
        importance_level="high",
    )
    assert critical["severity_category"] in ["severe", "critical"]
    assert critical["severity_score"] >= 60
    assert critical["urgency_days"] <= 14


def test_ai_explainability_gradcam(tmp_path):
    """Verify Explainable AI Grad-CAM heatmap generation."""
    img = np.full((128, 128, 3), 180, dtype=np.uint8)
    mask = np.zeros((128, 128), dtype=np.uint8)
    cv2.circle(mask, (64, 64), 20, 255, -1)

    out_file = tmp_path / "test_heatmap.jpg"
    res = generate_gradcam_heatmap(img, mask, out_file)
    assert res.is_file()
    assert res.stat().st_size > 0


def test_ai_damage_detection():
    """Verify multi-class surface defect detection."""
    img = np.full((150, 150, 3), 120, dtype=np.uint8)
    mask = np.zeros((150, 150), dtype=np.uint8)
    cv2.line(mask, (20, 20), (130, 130), 255, 3)

    result = detect_surface_defects(img, binary_mask=mask)
    assert "primary_defect" in result
    assert "confidence" in result
    assert "detections" in result
    assert len(result["detections"]) >= 1


def test_damage_progression_engine():
    """Verify multi-temporal crack growth tracking and deterioration classification."""
    current = {
        "crack_length_px": 250,
        "avg_width_px": 5.0,
        "max_width_px": 9.0,
        "crack_density_pct": 3.2,
        "severity_score": 68.0,
    }
    previous = {
        "crack_length_px": 200,
        "avg_width_px": 4.0,
        "max_width_px": 7.0,
        "crack_density_pct": 2.1,
        "severity_score": 52.0,
    }

    prog = analyze_damage_progression(earlier_finding=previous, latest_finding=current, days_elapsed=150)
    assert prog["delta_length_px"] == 50.0
    assert prog["length_growth_pct"] == 25.0
    assert prog["trend"] in ["minor_progression", "moderate_progression", "accelerated_deterioration"]


def test_maintenance_prioritization_engine():
    """Verify multi-factor maintenance scheduling priority."""
    actions = prioritize_maintenance(
        severity_category="critical",
        severity_score=88.0,
        defect_type="concrete_spalling",
        asset_type="bridge",
        importance_level="high",
        construction_year=1995,
        progression_trend="accelerated_deterioration",
    )
    assert actions["priority"] == "urgent_engineering_review"
    assert actions["urgency_days"] <= 30
    assert "recommended_technique" in actions
    assert "action_required" in actions


def test_automated_inspection_reports(tmp_path):
    """Verify automated PDF, CSV, and JSON inspection report creation."""
    with SessionLocal() as db:
        # Create a mock asset and inspection
        suffix = uuid.uuid4().hex[:6]
        asset = InfrastructureAsset(
            name=f"Bridge Test {suffix}",
            asset_type="bridge",
            material_type="concrete",
            latitude=13.0,
            longitude=80.0,
            construction_year=2018,
            responsible_department="QA Dept",
            importance_level="high",
        )
        db.add(asset)
        db.flush()

        insp = Inspection(
            asset_id=asset.asset_id,
            inspector_id=1,
            inspection_date=datetime.date(2026, 11, 20),
            status="completed",
        )
        db.add(insp)
        db.commit()

        # 1. PDF generation
        pdf_path = tmp_path / f"report_{insp.inspection_id}.pdf"
        generate_inspection_pdf(insp, asset, [], [], pdf_path)
        assert pdf_path.is_file()
        assert pdf_path.stat().st_size > 1000  # Valid PDF size

        # 2. CSV generation
        csv_path = tmp_path / f"report_{insp.inspection_id}.csv"
        generate_inspection_csv(insp, asset, [], [], csv_path)
        assert csv_path.is_file()
        assert "Inspection ID" in csv_path.read_text(encoding="utf-8")

        # 3. JSON generation
        json_path = tmp_path / f"report_{insp.inspection_id}.json"
        generate_inspection_json(insp, asset, [], [], json_path)
        assert json_path.is_file()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["inspection"]["inspection_id"] == insp.inspection_id


def test_notification_system():
    """Verify alert creation and retrieval."""
    with SessionLocal() as db:
        admin_user = db.query(User).filter(User.role == "admin").first()
        target_uid = admin_user.user_id if admin_user else 1

        n = create_notification(
            db=db,
            user_id=target_uid,
            title="Structural Alert",
            message="Severe crack detected on Bridge Pier 4",
            severity="critical",
        )
        assert n.notification_id is not None
        assert n.title == "Structural Alert"

        notifs = get_user_notifications(db, user_id=target_uid)
        assert len(notifs) >= 1
        assert any(item.notification_id == n.notification_id for item in notifs)


def test_api_milestones3_and_4():
    """Verify live API endpoints for dashboard stats, notifications, and maintenance."""
    # Login admin
    login_resp = client.post("/api/auth/login", json={"email": "gnanika20@gmail.com", "password": "password123"})
    if login_resp.status_code != 200:
        # Fallback to test user
        suffix = uuid.uuid4().hex[:6]
        client.post("/api/auth/register", json={"name": "Test Engineer", "email": f"eng-{suffix}@example.com", "password": "password123"})
        with SessionLocal() as db:
            u = db.query(User).filter(User.email == f"eng-{suffix}@example.com").first()
            if u:
                u.role = "admin"
                db.commit()
        login_resp = client.post("/api/auth/login", json={"email": f"eng-{suffix}@example.com", "password": "password123"})

    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Dashboard Stats
    stats_resp = client.get("/api/dashboard/stats", headers=headers)
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert "kpis" in data
    assert "total_assets" in data["kpis"]
    assert "severity_breakdown" in data

    # Notifications List
    notif_resp = client.get("/api/notifications", headers=headers)
    assert notif_resp.status_code == 200
    assert isinstance(notif_resp.json(), list)

    # Maintenance Priorities
    maint_resp = client.get("/api/maintenance/priorities", headers=headers)
    assert maint_resp.status_code == 200
    maint_data = maint_resp.json()
    assert "items" in maint_data or isinstance(maint_data, list)
