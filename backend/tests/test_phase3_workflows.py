"""End-to-End Test Suite for Phase 3 Role Workflows."""

from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.asset import InfrastructureAsset
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.maintenance import MaintenanceTask
from app.models.notification import Notification
from app.models.user import User
from app.services.security import hash_password

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db, email, role):
    u = User(
        full_name=f"Workflow {role}",
        email=email,
        password_hash=hash_password("WorkflowPass123!"),
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def get_headers(client, email):
    resp = client.post("/auth/login", data={"username": email, "password": "WorkflowPass123!"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_phase3_five_role_story_end_to_end(client: TestClient, db_session):
    """Execute complete Phase 3 story across 5 distinct roles."""
    # 0. Setup accounts for all 5 roles
    admin = make_user(db_session, "admin@workflow.test", "admin")
    manager = make_user(db_session, "manager@workflow.test", "manager")
    civil_eng = make_user(db_session, "civil@workflow.test", "civil_engineer")
    inspector = make_user(db_session, "inspector@workflow.test", "inspector")
    maint_eng = make_user(db_session, "maint@workflow.test", "maintenance_engineer")

    headers_admin = get_headers(client, admin.email)
    headers_mgr = get_headers(client, manager.email)
    headers_civil = get_headers(client, civil_eng.email)
    headers_insp = get_headers(client, inspector.email)
    headers_maint = get_headers(client, maint_eng.email)

    # 3.1 Manager creates an asset (with coordinates & district) and inspection assigned to inspector
    res_asset = client.post(
        "/assets",
        headers=headers_mgr,
        json={
            "name": "Kallanai Dam Section 4",
            "asset_type": "dam",
            "material_type": "concrete",
            "address": "Grand Anicut, Thanjavur",
            "latitude": 10.8305,
            "longitude": 78.8188,
            "district": "Thanjavur",
            "construction_year": 2010,
            "responsible_department": "Water Resources Dept",
            "inspection_frequency_days": 180,
            "importance_level": "high",
        },
    )
    assert res_asset.status_code == 201
    asset_id = res_asset.json()["asset_id"]

    res_insp = client.post(
        "/inspections",
        headers=headers_mgr,
        json={
            "asset_id": asset_id,
            "inspector_id": inspector.user_id,
            "inspection_date": str(date.today()),
            "status": "assigned",
        },
    )
    assert res_insp.status_code == 201
    inspection_id = res_insp.json()["inspection_id"]

    # Verify inspector received notification
    insp_notifs = db_session.query(Notification).filter(Notification.user_id == inspector.user_id).all()
    assert len(insp_notifs) >= 1
    assert any(n.type == "inspection_assigned" for n in insp_notifs)

    # 3.2 Inspector opens assignment and marks in_progress
    res_status = client.put(
        f"/inspections/{inspection_id}/status",
        headers=headers_insp,
        json={"status": "in_progress"},
    )
    assert res_status.status_code == 200

    # 3.3 Inspector marks inspection completed
    res_complete = client.put(
        f"/inspections/{inspection_id}/status",
        headers=headers_insp,
        json={"status": "completed"},
    )
    assert res_complete.status_code == 200

    # Verify civil engineers received notification requiring engineering review
    ce_notifs = db_session.query(Notification).filter(Notification.user_id == civil_eng.user_id).all()
    assert len(ce_notifs) >= 1
    assert any(n.type == "engineering_review_required" for n in ce_notifs)
    assert any("qualified engineering review required" in n.body.lower() or "engineer review" in n.body.lower() for n in ce_notifs)

    # 3.4 Civil engineer checks attention feed
    res_attn_ce = client.get("/dashboard/attention", headers=headers_civil)
    assert res_attn_ce.status_code == 200
    attn_ce_data = res_attn_ce.json()
    assert attn_ce_data["role"] == "civil_engineer"
    assert "disclaimer" in attn_ce_data

    # 3.5 Civil engineer creates maintenance task assigned to maintenance engineer
    res_task = client.post(
        "/maintenance/tasks",
        headers=headers_civil,
        json={
            "asset_id": asset_id,
            "inspection_id": inspection_id,
            "title": "Seal structural hairline cracks",
            "description": "Apply epoxy injection on Pier 4 cracks.",
            "priority": "P2",
            "assigned_to": maint_eng.user_id,
        },
    )
    assert res_task.status_code == 201
    task_id = res_task.json()["task_id"]

    # Verify maintenance engineer was notified
    maint_notifs = db_session.query(Notification).filter(Notification.user_id == maint_eng.user_id).all()
    assert len(maint_notifs) >= 1
    assert any(n.type == "task_assigned" for n in maint_notifs)

    # 3.6 Maintenance engineer sets task to in_progress, then completed with notes
    res_start = client.put(
        f"/maintenance/tasks/{task_id}/status",
        headers=headers_maint,
        json={"status": "in_progress"},
    )
    assert res_start.status_code == 200

    res_finish = client.put(
        f"/maintenance/tasks/{task_id}/status",
        headers=headers_maint,
        json={"status": "completed", "notes": "Epoxy seal applied thoroughly. Visual check OK."},
    )
    assert res_finish.status_code == 200

    # Civil engineer verifies task
    res_verify = client.put(
        f"/maintenance/tasks/{task_id}/verify",
        headers=headers_civil,
        json={"verified": True, "comment": "Work inspected and approved."},
    )
    assert res_verify.status_code == 200
    assert res_verify.json()["status"] == "verified"

    # 3.7 Civil engineer generates inspection report
    res_report = client.post(
        f"/inspections/{inspection_id}/reports",
        headers=headers_civil,
        json={"notes": "Final verified report."},
    )
    assert res_report.status_code == 201
    report_id = res_report.json()["report_id"]

    # Requester and manager receive report_ready notifications
    mgr_notifs = db_session.query(Notification).filter(Notification.user_id == manager.user_id).all()
    assert any(n.type == "report_ready" for n in mgr_notifs)

    # 3.8 Admin checks worker status and jobs endpoint
    res_worker = client.get("/jobs/worker/status", headers=headers_admin)
    assert res_worker.status_code == 200
    assert res_worker.json()["worker_status"] in ("online", "offline")

    # 3.9 Attention feeds for all roles return 200 and standard disclaimer
    for role_headers in [headers_admin, headers_mgr, headers_civil, headers_insp, headers_maint]:
        res_attn = client.get("/dashboard/attention", headers=role_headers)
        assert res_attn.status_code == 200
        assert "items" in res_attn.json()
        assert res_attn.json()["disclaimer"] == "AI result for engineer review, not a final structural safety verdict."

    # 3.10 RBAC enforcement: illegal actions return 403
    # Inspector cannot create maintenance task
    res_bad1 = client.post(
        "/maintenance/tasks",
        headers=headers_insp,
        json={"asset_id": asset_id, "title": "Illegal", "priority": "P1"},
    )
    assert res_bad1.status_code == 403

    # Maintenance engineer cannot verify maintenance task
    res_bad2 = client.put(
        f"/maintenance/tasks/{task_id}/verify",
        headers=headers_maint,
        json={"verified": True},
    )
    assert res_bad2.status_code == 403

    # Inspector cannot create asset
    res_bad3 = client.post(
        "/assets",
        headers=headers_insp,
        json={"name": "Bad Asset", "asset_type": "bridge"},
    )
    assert res_bad3.status_code == 403
