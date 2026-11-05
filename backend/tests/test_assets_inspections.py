from datetime import date
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.services.security import hash_password

# Use an in-memory SQLite database for isolated test execution
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


def create_user_helper(db_session, email, password, role, name="Test User"):
    user = User(
        full_name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def get_token_for_user(client, email, password):
    resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    return resp.json()["access_token"]


# 1. Admin creates an asset
def test_admin_creates_asset(client: TestClient, db_session):
    create_user_helper(db_session, "admin@test.com", "AdminPass123", "admin")
    admin_token = get_token_for_user(client, "admin@test.com", "AdminPass123")

    asset_payload = {
        "name": "Test Flyover B-1",
        "asset_type": "bridge",
        "material_type": "concrete",
        "address": "100 GST Road, Guindy",
        "latitude": 13.0067,
        "longitude": 80.2023,
        "construction_year": 2015,
        "responsible_department": "Highways Dept",
        "inspection_frequency_days": 90,
        "importance_level": "high",
    }

    response = client.post(
        "/assets",
        json=asset_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Flyover B-1"
    assert data["asset_type"] == "bridge"
    assert data["latitude"] == 13.0067


# 2. Inspector blocked from creating an asset (returns 403)
def test_inspector_blocked_from_creating(client: TestClient, db_session):
    create_user_helper(db_session, "insp@test.com", "InspPass123", "inspector")
    insp_token = get_token_for_user(client, "insp@test.com", "InspPass123")

    asset_payload = {
        "name": "Unauthorized Bridge",
        "asset_type": "bridge",
        "material_type": "concrete",
        "latitude": 13.0,
        "longitude": 80.0,
        "construction_year": 2020,
        "responsible_department": "PWD",
        "inspection_frequency_days": 60,
        "importance_level": "medium",
    }

    response = client.post(
        "/assets",
        json=asset_payload,
        headers={"Authorization": f"Bearer {insp_token}"},
    )
    assert response.status_code == 403


# 3. Invalid latitude rejected by Pydantic validation (returns 422)
def test_invalid_latitude_rejected(client: TestClient, db_session):
    create_user_helper(db_session, "admin2@test.com", "AdminPass123", "admin")
    admin_token = get_token_for_user(client, "admin2@test.com", "AdminPass123")

    bad_payload = {
        "name": "Invalid Geo Asset",
        "asset_type": "road",
        "material_type": "asphalt",
        "latitude": 115.5,  # Exceeds max 90.0
        "longitude": 80.2,
        "construction_year": 2020,
        "responsible_department": "PWD",
        "inspection_frequency_days": 60,
        "importance_level": "medium",
    }

    response = client.post(
        "/assets",
        json=bad_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


# 4. Search query filter works
def test_search_works(client: TestClient, db_session):
    create_user_helper(db_session, "admin3@test.com", "AdminPass123", "admin")
    admin_token = get_token_for_user(client, "admin3@test.com", "AdminPass123")
    auth_header = {"Authorization": f"Bearer {admin_token}"}

    client.post(
        "/assets",
        json={
            "name": "Kathipara Grade Separator",
            "asset_type": "bridge",
            "material_type": "concrete",
            "latitude": 13.0067,
            "longitude": 80.2023,
            "construction_year": 2008,
            "responsible_department": "Highways",
            "inspection_frequency_days": 90,
            "importance_level": "high",
        },
        headers=auth_header,
    )

    client.post(
        "/assets",
        json={
            "name": "Ennore Coastal Wall",
            "asset_type": "retaining_wall",
            "material_type": "concrete",
            "latitude": 13.2201,
            "longitude": 80.3255,
            "construction_year": 2015,
            "responsible_department": "Coastal",
            "inspection_frequency_days": 120,
            "importance_level": "medium",
        },
        headers=auth_header,
    )

    # Search for 'Kathipara'
    search_resp = client.get("/assets?search=Kathipara", headers=auth_header)
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] == 1
    assert "Kathipara" in search_data["items"][0]["name"]


# 5. Inspector sees only their own inspections
def test_inspector_sees_only_own_inspections(client: TestClient, db_session):
    admin = create_user_helper(db_session, "admin4@test.com", "AdminPass123", "admin")
    insp1 = create_user_helper(db_session, "insp1@test.com", "Pass12345", "inspector", name="Inspector One")
    insp2 = create_user_helper(db_session, "insp2@test.com", "Pass12345", "inspector", name="Inspector Two")

    admin_token = get_token_for_user(client, "admin4@test.com", "AdminPass123")
    insp1_token = get_token_for_user(client, "insp1@test.com", "Pass12345")

    # Admin creates asset
    asset_resp = client.post(
        "/assets",
        json={
            "name": "Corridor Bridge",
            "asset_type": "bridge",
            "material_type": "concrete",
            "latitude": 13.0,
            "longitude": 80.0,
            "construction_year": 2018,
            "responsible_department": "Transit",
            "inspection_frequency_days": 30,
            "importance_level": "high",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    asset_id = asset_resp.json()["asset_id"]

    # Admin schedules inspection for Inspector 1
    insp1_create = client.post(
        "/inspections",
        json={
            "asset_id": asset_id,
            "inspector_id": insp1.user_id,
            "inspection_date": str(date.today()),
            "status": "assigned",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert insp1_create.status_code == 201

    # Admin schedules inspection for Inspector 2
    insp2_create = client.post(
        "/inspections",
        json={
            "asset_id": asset_id,
            "inspector_id": insp2.user_id,
            "inspection_date": str(date.today()),
            "status": "assigned",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert insp2_create.status_code == 201
    insp2_id = insp2_create.json()["inspection_id"]

    # Inspector 1 lists inspections -> sees only 1 inspection
    list_resp = client.get("/inspections", headers={"Authorization": f"Bearer {insp1_token}"})
    assert list_resp.status_code == 200
    my_inspections = list_resp.json()
    assert len(my_inspections) == 1
    assert my_inspections[0]["inspector_id"] == insp1.user_id

    # Inspector 1 tries to view Inspector 2's inspection directly -> 403 Forbidden
    detail_resp = client.get(f"/inspections/{insp2_id}", headers={"Authorization": f"Bearer {insp1_token}"})
    assert detail_resp.status_code == 403


# 6. Deleting an asset with inspections is refused (returns 400)
def test_deleting_asset_with_inspections_refused(client: TestClient, db_session):
    admin = create_user_helper(db_session, "admin5@test.com", "AdminPass123", "admin")
    insp = create_user_helper(db_session, "insp3@test.com", "Pass12345", "inspector")

    admin_token = get_token_for_user(client, "admin5@test.com", "AdminPass123")
    admin_header = {"Authorization": f"Bearer {admin_token}"}

    # Create asset
    asset_resp = client.post(
        "/assets",
        json={
            "name": "Dam Section Alpha",
            "asset_type": "dam",
            "material_type": "masonry",
            "latitude": 13.01,
            "longitude": 80.05,
            "construction_year": 1975,
            "responsible_department": "Water",
            "inspection_frequency_days": 180,
            "importance_level": "high",
        },
        headers=admin_header,
    )
    asset_id = asset_resp.json()["asset_id"]

    # Create an inspection for this asset
    client.post(
        "/inspections",
        json={
            "asset_id": asset_id,
            "inspector_id": insp.user_id,
            "inspection_date": str(date.today()),
            "status": "assigned",
        },
        headers=admin_header,
    )

    # Attempt to delete the asset
    del_resp = client.delete(f"/assets/{asset_id}", headers=admin_header)
    assert del_resp.status_code == 400
    assert "inspection record(s) exist" in del_resp.json()["detail"]
