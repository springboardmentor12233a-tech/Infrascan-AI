import pytest
import io
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
import app.models
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


# --- 5. Test Work Orders CRUD (Module 16) ---
def test_work_orders_crud(client: TestClient, db_session):
    admin_token = get_user_token(client, db_session, "Administrator", "admin_wo_test")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create dummy asset
    asset_res = client.post("/assets/", json={
        "asset_code": "WO-ASSET-01",
        "name": "Maintenance Test Bridge",
        "type": "Bridge"
    }, headers=headers)
    asset_id = asset_res.json()["id"]

    # 1. Create work order
    wo_payload = {
        "asset_id": asset_id,
        "title": "Repair Abutment Concrete Spalling",
        "description": "Epoxy injection required on pier 3",
        "priority": "High Priority",
        "estimated_cost": 4500.0,
        "due_date": "2026-12-15"
    }
    create_res = client.post("/work-orders/", json=wo_payload, headers=headers)
    assert create_res.status_code == 201
    wo_data = create_res.json()
    assert wo_data["title"] == wo_payload["title"]
    assert wo_data["status"] == "Open"
    wo_id = wo_data["id"]

    # 2. List work orders
    list_res = client.get("/work-orders/", headers=headers)
    assert list_res.status_code == 200
    assert any(w["id"] == wo_id for w in list_res.json())

    # 3. Update work order status
    update_res = client.put(f"/work-orders/{wo_id}", json={
        "status": "In Progress",
        "resolution_notes": "Scaffolding erected on site."
    }, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "In Progress"
    assert update_res.json()["resolution_notes"] == "Scaffolding erected on site."

    # 4. Filter by status
    filter_res = client.get("/work-orders/?status_filter=In%20Progress", headers=headers)
    assert filter_res.status_code == 200
    assert any(w["id"] == wo_id for w in filter_res.json())


# --- 6. Test Notifications & Alerts (Module 20) ---
def test_notifications_endpoints(client: TestClient, db_session):
    admin_token = get_user_token(client, db_session, "Administrator", "admin_notif_test")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create custom alert
    create_res = client.post("/notifications/", json={
        "title": "Structural Alert Triggered",
        "message": "Critical crack aperture > 2.0mm detected on Bridge B-1",
        "severity": "Critical",
        "target_role": "Administrator"
    }, headers=headers)
    assert create_res.status_code == 201
    notif_id = create_res.json()["id"]

    # 2. List notifications
    list_res = client.get("/notifications/", headers=headers)
    assert list_res.status_code == 200
    assert any(n["id"] == notif_id for n in list_res.json())

    # 3. Mark single notification as read
    read_res = client.patch(f"/notifications/{notif_id}/read", headers=headers)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # 4. Mark all as read
    read_all_res = client.post("/notifications/read-all", headers=headers)
    assert read_all_res.status_code == 200


# --- 7. Test Multi-Format Reporting & Historical Progression (Modules 15 & 18) ---
def test_inspection_reports_and_progression(client: TestClient, db_session):
    admin_token = get_user_token(client, db_session, "Administrator", "admin_rep_test")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create asset & inspection
    asset_res = client.post("/assets/", json={
        "asset_code": "REP-ASSET-01",
        "name": "Report Test Dam",
        "type": "Dam"
    }, headers=headers)
    asset_id = asset_res.json()["id"]

    me_res = client.get("/auth/me", headers=headers)
    admin_id = me_res.json()["id"]

    insp_res = client.post("/inspections/", json={
        "asset_id": asset_id,
        "inspector_id": admin_id,
        "inspection_date": "2026-11-01"
    }, headers=headers)
    inspection_id = insp_res.json()["id"]

    # 1. CSV Report
    csv_res = client.get(f"/inspections/{inspection_id}/report/csv", headers=headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert "InfraScan" in csv_res.text

    # 2. Excel Report
    excel_res = client.get(f"/inspections/{inspection_id}/report/excel", headers=headers)
    assert excel_res.status_code == 200
    assert "spreadsheetml" in excel_res.headers.get("content-type", "")
    assert len(excel_res.content) > 100

    # 3. JSON Export
    json_res = client.get(f"/inspections/{inspection_id}/report/json", headers=headers)
    assert json_res.status_code == 200
    report_json = json_res.json()
    assert report_json["inspection_id"] == inspection_id
    assert "summary" in report_json
    assert "asset" in report_json
    assert "disclaimer" in report_json

    # 4. Asset Progression Timeline
    prog_res = client.get(f"/inspections/asset/{asset_id}/progression", headers=headers)
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert prog_data["asset_id"] == asset_id
    assert "timeline" in prog_data
    assert len(prog_data["timeline"]) >= 1


# --- 8. Test Model Versioning & Evaluation Metrics (Modules 11 & 21) ---
def test_model_versioning_and_metrics(client: TestClient, db_session):
    admin_token = get_user_token(client, db_session, "Administrator", "admin_model_test")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Evaluation metrics (confusion matrix, ROC, class metrics)
    metrics_res = client.get("/analytics/models/evaluation-metrics", headers=headers)
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert "confusion_matrix" in metrics
    assert "metrics" in metrics
    assert metrics["metrics"]["overall_accuracy"] > 90

    # 2. Model comparison registry
    comparison_res = client.get("/analytics/model-comparison", headers=headers)
    assert comparison_res.status_code == 200
    comp_data = comparison_res.json()
    assert "models" in comp_data
    assert len(comp_data["models"]) >= 4

    # 3. Deploy/activate model
    deploy_res = client.post("/analytics/models/yolov8_detector/deploy", headers=headers)
    assert deploy_res.status_code == 200
    assert "deployed" in deploy_res.json()["message"].lower()
    assert deploy_res.json()["active_model"]["id"] == "yolov8_detector"

