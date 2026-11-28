"""
Pytest suite for InfraScan backend.

Run from backend/ directory:
    pytest tests/ -v

Uses the same SQLite database in dev mode (no separate test DB needed).
"""

import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def engineer_token(client):
    email = f"test.engineer.{int(time.time())}@infrascan.dev"
    res = client.post("/api/v1/auth/register", json={
        "full_name": "Test Engineer",
        "email": email,
        "password": "testpass123",
        "role": "Engineer",
    })
    assert res.status_code == 201, f"Register failed: {res.text}"
    data = res.json()
    return {"token": data["access_token"], "email": email}


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_register_new_user(client):
    email = f"newuser_{int(time.time())}@infrascan.dev"
    res = client.post("/api/v1/auth/register", json={
        "full_name": "New User",
        "email": email,
        "password": "newpassword99",
        "role": "Viewer",
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == email


def test_register_duplicate_email(client):
    email = f"dup_{int(time.time())}@infrascan.dev"
    # First registration
    res1 = client.post("/api/v1/auth/register", json={
        "full_name": "Dup User",
        "email": email,
        "password": "password123",
    })
    assert res1.status_code == 201
    # Second should conflict
    res2 = client.post("/api/v1/auth/register", json={
        "full_name": "Dup User",
        "email": email,
        "password": "password123",
    })
    assert res2.status_code == 409


def test_login_success(client, engineer_token):
    assert len(engineer_token["token"]) > 10


def test_login_wrong_password(client, engineer_token):
    res = client.post("/api/v1/auth/login", json={
        "email": engineer_token["email"],
        "password": "wrongpassword",
    })
    assert res.status_code == 401


def test_me_authenticated(client, engineer_token):
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {engineer_token['token']}"})
    assert res.status_code == 200
    assert res.json()["email"] == engineer_token["email"]


def test_me_unauthenticated(client):
    res = client.get("/api/v1/auth/me")
    # HTTPBearer returns 403 when credentials are missing
    assert res.status_code in (401, 403)


# ── Assets ────────────────────────────────────────────────────────────────────

def test_create_asset(client, engineer_token):
    h = {"Authorization": f"Bearer {engineer_token['token']}"}
    res = client.post("/api/v1/assets", json={
        "asset_code": f"TEST-BRG-{int(time.time())}",
        "name": "Test Bridge",
        "infrastructure_type": "Bridge",
        "location_name": "Test Location",
        "construction_year": 2000,
    }, headers=h)
    assert res.status_code == 201
    assert res.json()["name"] == "Test Bridge"


def test_create_asset_duplicate_code(client, engineer_token):
    h = {"Authorization": f"Bearer {engineer_token['token']}"}
    code = f"TEST-DUP-{int(time.time())}"
    # Create first
    client.post("/api/v1/assets", json={
        "asset_code": code,
        "name": "Dup Asset",
        "infrastructure_type": "Building",
        "location_name": "Somewhere",
    }, headers=h)
    # Create second with same code
    res = client.post("/api/v1/assets", json={
        "asset_code": code,
        "name": "Another Asset",
        "infrastructure_type": "Bridge",
        "location_name": "Elsewhere",
    }, headers=h)
    assert res.status_code == 409


def test_list_assets(client, engineer_token):
    h = {"Authorization": f"Bearer {engineer_token['token']}"}
    res = client.get("/api/v1/assets", headers=h)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_get_asset(client, engineer_token):
    h = {"Authorization": f"Bearer {engineer_token['token']}"}
    res = client.post("/api/v1/assets", json={
        "asset_code": f"TEST-GET-{int(time.time())}",
        "name": "Get Asset",
        "infrastructure_type": "Tunnel",
        "location_name": "Tunnel Location",
    }, headers=h)
    asset_id = res.json()["id"]
    get_res = client.get(f"/api/v1/assets/{asset_id}", headers=h)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == asset_id


def test_archive_asset(client, engineer_token):
    h = {"Authorization": f"Bearer {engineer_token['token']}"}
    res = client.post("/api/v1/assets", json={
        "asset_code": f"TEST-ARC-{int(time.time())}",
        "name": "Archive Asset",
        "infrastructure_type": "Dam",
        "location_name": "Dam Site",
    }, headers=h)
    asset_id = res.json()["id"]
    del_res = client.delete(f"/api/v1/assets/{asset_id}", headers=h)
    assert del_res.status_code == 204


# ── Inspections ───────────────────────────────────────────────────────────────

def test_create_inspection_missing_asset(client, engineer_token):
    h = {"Authorization": f"Bearer {engineer_token['token']}"}
    res = client.post("/api/v1/inspections", json={
        "inspection_code": f"INSP-NOASSET-{int(time.time())}",
        "asset_id": "00000000-0000-0000-0000-000000000000",
        "inspection_type": "Routine Inspection",
        "inspection_date": "2026-12-01",
    }, headers=h)
    assert res.status_code == 404
