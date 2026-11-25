import json
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.event import Event, EventTicket
from app.models.user import User
from app.services.event_service import (
    broker,
    can_user_see,
    create_event_ticket,
    get_events_since,
    publish,
    purge_old_events,
    validate_and_consume_ticket,
)
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
        full_name=f"Test {role}",
        email=email,
        password_hash=hash_password("RealtimePassword123!"),
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def get_token(client, email):
    resp = client.post("/auth/login", data={"username": email, "password": "RealtimePassword123!"})
    return resp.json()["access_token"]


def test_ticket_generation_and_single_use(client: TestClient, db_session):
    user = make_user(db_session, "user.ticket@test.com", "civil_engineer")
    token = get_token(client, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Generate ticket
    res = client.post("/events/ticket", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "ticket" in data
    assert data["expires_in"] == 30
    assert len(data["ticket"]) == 64  # 32 bytes hex

    ticket = data["ticket"]

    # 2. Consume ticket once
    validated_user = validate_and_consume_ticket(db_session, ticket)
    assert validated_user is not None
    assert validated_user.user_id == user.user_id

    # 3. Second consumption must be blocked (single-use replay prevention)
    reused = validate_and_consume_ticket(db_session, ticket)
    assert reused is None


def test_ticket_expiry(db_session):
    user = make_user(db_session, "user.expired@test.com", "inspector")
    # Create ticket already expired 1 second ago
    ticket = create_event_ticket(db_session, user, expiry_seconds=-1)
    consumed = validate_and_consume_ticket(db_session, ticket)
    assert consumed is None


def test_audience_filtering_and_role_isolation(db_session):
    admin = make_user(db_session, "admin.live@test.com", "admin")
    insp1 = make_user(db_session, "insp1.live@test.com", "inspector")
    insp2 = make_user(db_session, "insp2.live@test.com", "inspector")
    maint = make_user(db_session, "maint.live@test.com", "maintenance_engineer")
    civil = make_user(db_session, "civil.live@test.com", "civil_engineer")

    # Event 1: Inspection created for Inspector 1
    insp1_event = Event(
        type="inspection.created",
        entity_type="inspection",
        entity_id="101",
        audience_json={"roles": ["admin", "manager", "civil_engineer", "inspector"], "inspector_id": insp1.user_id},
        payload_json={"inspection_id": 101, "inspector_id": insp1.user_id},
    )

    assert can_user_see(admin, insp1_event) is True
    assert can_user_see(civil, insp1_event) is True
    assert can_user_see(insp1, insp1_event) is True
    # Inspector 2 must NOT receive inspector 1's scoped inspection event
    assert can_user_see(insp2, insp1_event) is False

    # Event 2: Provisional severity calculated (unconfirmed)
    prov_sev_event = Event(
        type="severity.assessed",
        entity_type="severity_assessment",
        entity_id="201",
        audience_json={"roles": ["admin", "manager", "civil_engineer"]},
        payload_json={"assessment_id": 201, "is_confirmed": False, "severity_level": "critical"},
    )

    assert can_user_see(admin, prov_sev_event) is True
    assert can_user_see(civil, prov_sev_event) is True
    # Maintenance engineer must NEVER see unconfirmed/provisional severity
    assert can_user_see(maint, prov_sev_event) is False

    # Event 3: Confirmed severity
    conf_sev_event = Event(
        type="severity.confirmed",
        entity_type="severity_assessment",
        entity_id="201",
        audience_json={"all": True},
        payload_json={"assessment_id": 201, "is_confirmed": True, "final_severity": "critical"},
    )
    assert can_user_see(maint, conf_sev_event) is True
    assert can_user_see(insp1, conf_sev_event) is True


def test_polling_fallback_and_replay(client: TestClient, db_session):
    admin = make_user(db_session, "admin.poll@test.com", "admin")
    insp = make_user(db_session, "insp.poll@test.com", "inspector")

    token_admin = get_token(client, admin.email)
    token_insp = get_token(client, insp.email)

    # Publish events
    e1 = publish(
        db=db_session,
        event_type="asset.created",
        entity_type="asset",
        entity_id="1",
        audience={"all": True},
        payload={"asset_id": 1, "name": "Highway Overpass"},
    )
    e2 = publish(
        db=db_session,
        event_type="inspection.assigned",
        entity_type="inspection",
        entity_id="10",
        audience={"user_ids": [insp.user_id], "roles": ["admin"]},
        payload={"inspection_id": 10, "inspector_id": insp.user_id},
    )
    db_session.commit()

    # Poll as Inspector: should see both asset.created (all) and inspection.assigned (scoped to insp)
    res_insp = client.get(f"/events/poll?since_id=0", headers={"Authorization": f"Bearer {token_insp}"})
    assert res_insp.status_code == 200
    data_insp = res_insp.json()
    assert data_insp["count"] == 2
    assert data_insp["last_id"] == e2.event_id

    # Replay with since_id = e1.event_id
    res_replay = client.get(f"/events/poll?since_id={e1.event_id}", headers={"Authorization": f"Bearer {token_insp}"})
    assert res_replay.status_code == 200
    data_replay = res_replay.json()
    assert data_replay["count"] == 1
    assert data_replay["events"][0]["event_id"] == e2.event_id


def test_stream_concurrent_limit_per_user(client: TestClient, db_session):
    user = make_user(db_session, "limit.user@test.com", "inspector")
    uid = user.user_id

    # Acquire 5 streams
    for _ in range(5):
        assert broker.acquire_stream(uid) is True

    # 6th stream must be rejected
    assert broker.acquire_stream(uid) is False

    # Release one stream
    broker.release_stream(uid)
    assert broker.acquire_stream(uid) is True

    # Clean up releases
    for _ in range(5):
        broker.release_stream(uid)


def test_retention_purge(db_session):
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=8)

    old_event = Event(
        type="asset.created",
        entity_type="asset",
        entity_id="999",
        audience_json={"all": True},
        payload_json={"name": "Old Asset"},
        created_at=old_date,
    )
    new_event = Event(
        type="asset.created",
        entity_type="asset",
        entity_id="1000",
        audience_json={"all": True},
        payload_json={"name": "New Asset"},
        created_at=now,
    )
    db_session.add_all([old_event, new_event])
    db_session.commit()

    purged_count = purge_old_events(db_session, max_age_days=7)
    assert purged_count >= 1

    remaining = db_session.query(Event).filter(Event.entity_id == "999").first()
    assert remaining is None

    kept = db_session.query(Event).filter(Event.entity_id == "1000").first()
    assert kept is not None
