import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.main import app
from app.db import SessionLocal
from app.models.user import User

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
    # Promote to admin for asset management authorization
    with SessionLocal() as db:
        u = db.query(User).filter(User.email == email).first()
        if u:
            u.role = "admin"
            db.commit()
    login = client.post("/api/auth/login", json={"email": email, "password": "secure123"})
    assert login.status_code == 200 or login.status_code == 201
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": f"Test Flyover {suffix}",
        "asset_type": "bridge",
        "material_type": "concrete",
        "address": "100 GST Road",
        "latitude": 13.0067,
        "longitude": 80.2023,
        "construction_year": 2020,
        "responsible_department": "Testing",
        "inspection_frequency_days": 90,
        "importance_level": "medium",
    }
    created = client.post("/api/assets", json=payload, headers=headers)
    assert created.status_code in (201, 409)
    asset_id = created.json()["asset_id"]
    updated = {**payload, "name": "Updated test bridge"}
    update = client.put(f"/api/assets/{asset_id}", json=updated, headers=headers)
    assert update.status_code == 200
    assert update.json()["name"] == "Updated test bridge"
    deleted = client.delete(f"/api/assets/{asset_id}", headers=headers)
    assert deleted.status_code in (200, 204)
