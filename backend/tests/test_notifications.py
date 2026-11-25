import json
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.asset import InfrastructureAsset
from app.models.maintenance import MaintenanceTask
from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.services.notification_service import (
    create_notification,
    get_or_create_preference,
    notify_roles,
    send_email_notification,
    sweep_deadlines_and_overdue,
)
from app.services.security import create_access_token, hash_password

# Test SQLite in-memory DB
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


def make_user(db_session, email="alice@example.com", role="inspector", full_name="Alice Inspector"):
    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password("Password123!"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def make_auth_headers(user: User) -> dict:
    token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.user_id})
    return {"Authorization": f"Bearer {token}"}


def test_notification_creation_and_unread_flow(client: TestClient, db_session):
    user = make_user(db_session, "user1@example.com", "inspector")
    headers = make_auth_headers(user)

    # 1. Initially zero notifications
    resp = client.get("/notifications", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["unread_count"] == 0

    # 2. Trigger notification
    notif = create_notification(
        db=db_session,
        user_id=user.user_id,
        type="inspection_assigned",
        title="New Inspection Assigned",
        body="Inspection #101 scheduled for Bridge Alpha.",
        entity_type="inspection",
        entity_id="101",
    )
    assert notif is not None
    assert notif.id is not None

    # 3. Check unread count endpoint
    resp_count = client.get("/notifications/unread-count", headers=headers)
    assert resp_count.status_code == 200
    assert resp_count.json()["unread_count"] == 1

    # 4. Check list
    resp_list = client.get("/notifications", headers=headers)
    data = resp_list.json()
    assert data["total"] == 1
    assert data["unread_count"] == 1
    item = data["items"][0]
    assert item["id"] == notif.id
    assert item["type"] == "inspection_assigned"
    assert item["is_read"] is False

    # 5. Mark as read
    resp_read = client.post(f"/notifications/{notif.id}/read", headers=headers)
    assert resp_read.status_code == 200
    assert resp_read.json()["is_read"] is True

    # 6. Unread count is now 0
    resp_count2 = client.get("/notifications/unread-count", headers=headers)
    assert resp_count2.json()["unread_count"] == 0


def test_notification_deduplication(db_session):
    user = make_user(db_session, "dedup@example.com", "civil_engineer")

    # First call creates notification
    n1 = create_notification(
        db=db_session,
        user_id=user.user_id,
        type="damage_detected",
        title="Damage Detected",
        body="Cracks found on Pier 4.",
        entity_type="inspection",
        entity_id="202",
    )
    assert n1 is not None

    # Immediate second call with identical parameters returns existing notification without duplicate DB insert
    n2 = create_notification(
        db=db_session,
        user_id=user.user_id,
        type="damage_detected",
        title="Damage Detected",
        body="Cracks found on Pier 4.",
        entity_type="inspection",
        entity_id="202",
    )
    assert n2 is not None
    assert n1.id == n2.id

    # Total in DB must be 1
    total = db_session.query(Notification).filter(Notification.user_id == user.user_id).count()
    assert total == 1


def test_read_all_notifications(client: TestClient, db_session):
    user = make_user(db_session, "readall@example.com", "inspector")
    headers = make_auth_headers(user)

    # Create 3 distinct notifications
    for i in range(1, 4):
        create_notification(
            db=db_session,
            user_id=user.user_id,
            type="inspection_assigned",
            title=f"Inspection #{i}",
            body=f"Details for #{i}",
            entity_type="inspection",
            entity_id=str(i),
        )

    assert client.get("/notifications/unread-count", headers=headers).json()["unread_count"] == 3

    # Mark all read
    resp = client.post("/notifications/read-all", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["marked_read"] == 3

    # Verify unread count is 0
    assert client.get("/notifications/unread-count", headers=headers).json()["unread_count"] == 0


def test_user_preferences_severity_filtering(client: TestClient, db_session):
    user = make_user(db_session, "pref@example.com", "civil_engineer")
    headers = make_auth_headers(user)

    # 1. Update preferences to 'high' minimum severity
    resp = client.put(
        "/notifications/preferences",
        json={"min_severity": "high", "in_app_enabled": True, "email_enabled": False},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_severity"] == "high"
    assert data["email_enabled"] is False

    # 2. Create notification with 'low' severity -> should be suppressed
    n_low = create_notification(
        db=db_session,
        user_id=user.user_id,
        type="damage_detected",
        title="Low crack width",
        body="Minor hairline crack.",
        entity_type="image",
        entity_id="10",
        severity="low",
    )
    assert n_low is None

    # 3. Create notification with 'critical' severity -> should be created
    n_crit = create_notification(
        db=db_session,
        user_id=user.user_id,
        type="critical_alert",
        title="Critical Structural Defect",
        body="Major spalling detected.",
        entity_type="image",
        entity_id="11",
        severity="critical",
    )
    assert n_crit is not None
    assert n_crit.id is not None


def test_email_failure_isolation(db_session):
    user = make_user(db_session, "email_iso@example.com", "civil_engineer")

    # send_email_notification to nonexistent/closed port must not raise
    success = send_email_notification(
        to_email=user.email,
        subject="Test Alert",
        body_text="Test body message.",
    )
    # Should cleanly return False (or True if simulated) without throwing
    assert isinstance(success, bool)

    # Notification creation succeeds even if email fails
    n = create_notification(
        db=db_session,
        user_id=user.user_id,
        type="critical_alert",
        title="Urgent Notice",
        body="Qualified review required.",
        entity_type="inspection",
        entity_id="999",
    )
    assert n is not None
    assert n.id is not None


def test_notification_sweep(client: TestClient, db_session):
    admin = make_user(db_session, "admin_sweep@example.com", "admin")
    maint_eng = make_user(db_session, "maint@example.com", "maintenance_engineer")
    headers = make_auth_headers(admin)

    # Setup asset overdue for inspection
    asset = InfrastructureAsset(
        name="Overdue Viaduct",
        asset_type="bridge",
        material_type="concrete",
        latitude=37.77,
        longitude=-122.42,
        construction_year=1980,
        responsible_department="Public Works",
        inspection_frequency_days=365,
        importance_level="high",
        next_inspection_due=(datetime.now(timezone.utc) - timedelta(days=5)).date(),
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    # Setup maintenance task due tomorrow
    task = MaintenanceTask(
        asset_id=asset.asset_id,
        title="Emergency Joint Seal",
        description="Seal joint before freeze",
        task_type="repair",
        priority="P1",
        status="open",
        assigned_to=maint_eng.user_id,
        due_date=(datetime.now(timezone.utc) + timedelta(days=1)).date(),
    )
    db_session.add(task)
    db_session.commit()

    # Trigger sweep via API
    resp = client.post("/notifications/sweep", headers=headers)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["maintenance_alerts"] >= 1
    assert res_data["overdue_inspections"] >= 1

    # Check that maintenance engineer received the alert
    maint_headers = make_auth_headers(maint_eng)
    maint_notifs = client.get("/notifications", headers=maint_headers).json()
    assert maint_notifs["total"] >= 1
    assert "Emergency Joint Seal" in maint_notifs["items"][0]["title"]
