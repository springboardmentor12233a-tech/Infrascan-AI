import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_register_login_and_asset_crud():
    suffix = uuid.uuid4().hex[:8]
    email = f"milestone1-{suffix}@example.com"
    register = client.post("/api/auth/register", json={"name": "Milestone One", "email": email, "password": "secure123"})
    assert register.status_code in (201, 409)
    if register.status_code == 409:
        login = client.post("/api/auth/login", json={"email": email, "password": "secure123"})
    else:
        login = register
    assert login.status_code == 200 or login.status_code == 201
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    asset_id = f"TEST-M1-{suffix}"
    payload = {
        "asset_id": asset_id,
        "name": "Milestone test bridge",
        "type": "Bridge",
        "location": "Test location",
        "construction_year": 2020,
        "material": "Concrete",
        "department": "Testing",
        "inspection_frequency": "Monthly",
        "maintenance_history": "None",
    }
    created = client.post("/api/assets", json=payload, headers=headers)
    assert created.status_code in (201, 409)
    updated = {**payload, "name": "Updated test bridge"}
    update = client.put(f"/api/assets/{asset_id}", json=updated, headers=headers)
    assert update.status_code == 200
    assert update.json()["name"] == "Updated test bridge"
    deleted = client.delete(f"/api/assets/{asset_id}", headers=headers)
    assert deleted.status_code == 204
