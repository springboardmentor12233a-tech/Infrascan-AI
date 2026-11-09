import pytest
import io
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.role import Role, ROLE_NAMES
from app.models.infrastructure_asset import InfrastructureAsset, AssetType
from app.services.seed import seed_roles

# Create in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_roles(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
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


# Helper to register and login a user with a specific role
def get_user_token(client: TestClient, db_session, role_name: str, email_prefix: str = "user"):
    role = db_session.query(Role).filter(Role.name == role_name).first()
    email = f"{email_prefix}_{role_name.lower().replace(' ', '_')}@test.com"
    password = "TestPassword123!"

    # Register
    reg_res = client.post("/auth/register", json={
        "email": email,
        "full_name": f"Test {role_name}",
        "password": password,
        "role_id": role.id
    })
    
    # Login
    login_res = client.post("/auth/login", data={
        "username": email,
        "password": password
    })
    return login_res.json()["access_token"]


# --- 1. Test Register and Login ---
def test_register_and_login(client: TestClient, db_session):
    email = "new_engineer@test.com"
    res = client.post("/auth/register", json={
        "email": email,
        "full_name": "Civil Bob",
        "password": "Password123!"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == email

    # Login
    login_res = client.post("/auth/login", data={
        "username": email,
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


# --- 2. Test Role Denial (403) ---
def test_role_denial_admin_endpoint(client: TestClient, db_session):
    # Inspector token
    inspector_token = get_user_token(client, db_session, "Infrastructure Inspector", "insp_role_test")
    headers = {"Authorization": f"Bearer {inspector_token}"}

    # Inspectors should NOT be able to access GET /users (Admin only)
    res = client.get("/users/", headers=headers)
    assert res.status_code == 403


# --- 3. Test Asset CRUD ---
def test_asset_crud(client: TestClient, db_session):
    manager_token = get_user_token(client, db_session, "Infrastructure Manager", "mgr_asset_test")
    headers = {"Authorization": f"Bearer {manager_token}"}

    # Create Asset
    create_payload = {
        "asset_code": "TEST-BRG-99",
        "name": "Test Highway Bridge",
        "type": "Bridge",
        "latitude": 34.05,
        "longitude": -118.25,
        "construction_year": 1999
    }
    create_res = client.post("/assets/", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    asset_id = create_res.json()["id"]

    # Read Asset
    get_res = client.get(f"/assets/{asset_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Test Highway Bridge"

    # Update Asset
    update_res = client.put(f"/assets/{asset_id}", json={"name": "Updated Highway Bridge"}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Highway Bridge"

    # Delete Asset
    del_res = client.delete(f"/assets/{asset_id}", headers=headers)
    assert del_res.status_code == 204


# --- 4. Test Image Upload Validations (bad format, tiny, duplicate, blurry) ---
def test_image_validations(client: TestClient, db_session):
    admin_token = get_user_token(client, db_session, "Administrator", "admin_img_test")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create dummy asset and inspection
    asset_res = client.post("/assets/", json={
        "asset_code": "TEST-IMG-ASSET",
        "name": "Image Inspection Asset",
        "type": "Road"
    }, headers=headers)
    asset_id = asset_res.json()["id"]

    # Create inspection
    me_res = client.get("/auth/me", headers=headers)
    admin_id = me_res.json()["id"]

    insp_res = client.post("/inspections/", json={
        "asset_id": asset_id,
        "inspector_id": admin_id,
        "inspection_date": "2026-10-18"
    }, headers=headers)
    inspection_id = insp_res.json()["id"]

    # A. Bad format validation
    fake_txt = io.BytesIO(b"not an image text content")
    bad_res = client.post(
        f"/inspections/{inspection_id}/images",
        headers=headers,
        files={"files": ("test.txt", fake_txt, "text/plain")}
    )
    assert bad_res.status_code == 400
    assert "Invalid file type" in bad_res.json()["detail"]

    # B. Tiny image validation (< 64x64)
    tiny_img = Image.new("RGB", (32, 32), color="blue")
    tiny_buf = io.BytesIO()
    tiny_img.save(tiny_buf, format="JPEG")
    tiny_buf.seek(0)

    tiny_res = client.post(
        f"/inspections/{inspection_id}/images",
        headers=headers,
        files={"files": ("tiny.jpg", tiny_buf, "image/jpeg")}
    )
    assert tiny_res.status_code == 400
    assert "too small" in tiny_res.json()["detail"]

    # C. Valid image upload + Blur validation check
    # A completely solid grey image produces Laplacian variance of 0.0 -> flagged as 'blurry'
    blurry_img = Image.new("RGB", (128, 128), color=(128, 128, 128))
    img_buf = io.BytesIO()
    blurry_img.save(img_buf, format="JPEG")
    img_buf.seek(0)
    img_bytes = img_buf.getvalue()

    ok_res = client.post(
        f"/inspections/{inspection_id}/images",
        headers=headers,
        files={"files": ("blurry.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    )
    assert ok_res.status_code == 201
    uploaded = ok_res.json()
    assert len(uploaded) == 1
    assert uploaded[0]["quality_status"] == "blurry"

    # D. Duplicate rejection check (upload same exact bytes to same inspection)
    dup_res = client.post(
        f"/inspections/{inspection_id}/images",
        headers=headers,
        files={"files": ("duplicate.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    )
    assert dup_res.status_code == 400
    assert "Duplicate image detected" in dup_res.json()["detail"]
