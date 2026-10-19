from datetime import date
import io
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models.asset import InfrastructureAsset
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
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
def db_session(tmp_path, monkeypatch):
    # Route upload files to temporary pytest directory
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))

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


# Helpers to generate test images in-memory with Pillow
def generate_sharp_image(width=800, height=600) -> bytes:
    """Generate high-contrast grid image with high Laplacian variance (> 100)."""
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    draw = ImageDraw.Draw(img)
    for i in range(0, max(width, height), 25):
        draw.line([(i, 0), (i, height)], fill=(255, 255, 255), width=3)
        draw.line([(0, i), (width, i)], fill=(0, 0, 0), width=3)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def generate_blurry_image(width=800, height=600) -> bytes:
    """Generate solid uniform image with zero edge variance to trigger blur warning."""
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def generate_tiny_image(width=200, height=150) -> bytes:
    """Generate sub-resolution image below 640x480."""
    img = Image.new("RGB", (width, height), color=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def setup_asset_and_inspection(db_session, inspector_user):
    asset = InfrastructureAsset(
        name="Test Pier 4",
        asset_type="bridge",
        material_type="concrete",
        latitude=13.0,
        longitude=80.0,
        construction_year=2010,
        responsible_department="PWD",
        inspection_frequency_days=90,
        importance_level="high",
    )
    db_session.add(asset)
    db_session.commit()

    inspection = Inspection(
        asset_id=asset.asset_id,
        inspector_id=inspector_user.user_id,
        inspection_date=date.today(),
        status="assigned",
    )
    db_session.add(inspection)
    db_session.commit()
    db_session.refresh(inspection)
    return asset, inspection


def create_user(db_session, email, role, name="Test"):
    user = User(
        full_name=name,
        email=email,
        password_hash=hash_password("Pass12345"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def get_token(client, email):
    resp = client.post("/auth/login", data={"username": email, "password": "Pass12345"})
    return resp.json()["access_token"]


# 1. Valid image accepted & inspection status promoted to in_progress
def test_valid_image_accepted(client: TestClient, db_session):
    insp_user = create_user(db_session, "insp1@test.com", "inspector")
    _, inspection = setup_asset_and_inspection(db_session, insp_user)
    token = get_token(client, "insp1@test.com")

    image_bytes = generate_sharp_image(800, 600)
    files = [("files", ("photo.jpg", image_bytes, "image/jpeg"))]

    resp = client.post(
        f"/inspections/{inspection.inspection_id}/images",
        headers={"Authorization": f"Bearer {token}"},
        data={"source": "phone"},
        files=files,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["accepted_count"] == 1
    assert data["results"][0]["status"] == "accepted"

    # Status should have automatically progressed from 'assigned' to 'in_progress'
    db_session.refresh(inspection)
    assert inspection.status == "in_progress"


# 2. Text file renamed to .jpg rejected
def test_text_file_renamed_to_jpg_rejected(client: TestClient, db_session):
    insp_user = create_user(db_session, "insp2@test.com", "inspector")
    _, inspection = setup_asset_and_inspection(db_session, insp_user)
    token = get_token(client, "insp2@test.com")

    fake_bytes = b"Hello, this is not an image but a plain text file renamed to fake.jpg"
    files = [("files", ("fake.jpg", fake_bytes, "image/jpeg"))]

    resp = client.post(
        f"/inspections/{inspection.inspection_id}/images",
        headers={"Authorization": f"Bearer {token}"},
        data={"source": "phone"},
        files=files,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rejected_count"] == 1
    assert data["results"][0]["status"] == "rejected"
    assert "Invalid or corrupted image" in data["results"][0]["message"]


# 3. Tiny image rejected (< 640x480)
def test_tiny_image_rejected(client: TestClient, db_session):
    insp_user = create_user(db_session, "insp3@test.com", "inspector")
    _, inspection = setup_asset_and_inspection(db_session, insp_user)
    token = get_token(client, "insp3@test.com")

    tiny_bytes = generate_tiny_image(200, 150)
    files = [("files", ("tiny.jpg", tiny_bytes, "image/jpeg"))]

    resp = client.post(
        f"/inspections/{inspection.inspection_id}/images",
        headers={"Authorization": f"Bearer {token}"},
        data={"source": "phone"},
        files=files,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rejected_count"] == 1
    assert data["results"][0]["status"] == "rejected"
    assert "resolution" in data["results"][0]["message"].lower()


# 4. Duplicate rejected
def test_duplicate_rejected(client: TestClient, db_session):
    insp_user = create_user(db_session, "insp4@test.com", "inspector")
    _, inspection = setup_asset_and_inspection(db_session, insp_user)
    token = get_token(client, "insp4@test.com")

    image_bytes = generate_sharp_image(800, 600)

    # First upload -> accepted
    resp1 = client.post(
        f"/inspections/{inspection.inspection_id}/images",
        headers={"Authorization": f"Bearer {token}"},
        data={"source": "phone"},
        files=[("files", ("photo.jpg", image_bytes, "image/jpeg"))],
    )
    assert resp1.json()["accepted_count"] == 1

    # Second upload with identical bytes -> rejected with reason "duplicate"
    resp2 = client.post(
        f"/inspections/{inspection.inspection_id}/images",
        headers={"Authorization": f"Bearer {token}"},
        data={"source": "phone"},
        files=[("files", ("photo_copy.jpg", image_bytes, "image/jpeg"))],
    )
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert data2["rejected_count"] == 1
    assert data2["results"][0]["status"] == "rejected"
    assert data2["results"][0]["message"] == "duplicate"


# 5. Blurry image gives a warning but is saved
def test_blurry_image_gives_warning_but_saved(client: TestClient, db_session):
    insp_user = create_user(db_session, "insp5@test.com", "inspector")
    _, inspection = setup_asset_and_inspection(db_session, insp_user)
    token = get_token(client, "insp5@test.com")

    blurry_bytes = generate_blurry_image(800, 600)
    files = [("files", ("blurry.jpg", blurry_bytes, "image/jpeg"))]

    resp = client.post(
        f"/inspections/{inspection.inspection_id}/images",
        headers={"Authorization": f"Bearer {token}"},
        data={"source": "camera"},
        files=files,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["warning_count"] == 1
    assert data["results"][0]["status"] == "warning"
    assert "blurry" in data["results"][0]["message"].lower()

    # Image is still saved to the database
    img_record = db_session.query(ImageModel).filter(ImageModel.inspection_id == inspection.inspection_id).first()
    assert img_record is not None
    assert img_record.quality_status == "warning"


# 6. An inspector cannot upload to someone else's inspection
def test_inspector_cannot_upload_to_someone_elses_inspection(client: TestClient, db_session):
    insp1 = create_user(db_session, "owner@test.com", "inspector", name="Inspector 1")
    insp2 = create_user(db_session, "intruder@test.com", "inspector", name="Inspector 2")
    _, inspection = setup_asset_and_inspection(db_session, insp1)

    intruder_token = get_token(client, "intruder@test.com")
    image_bytes = generate_sharp_image(800, 600)

    resp = client.post(
        f"/inspections/{inspection.inspection_id}/images",
        headers={"Authorization": f"Bearer {intruder_token}"},
        data={"source": "phone"},
        files=[("files", ("photo.jpg", image_bytes, "image/jpeg"))],
    )
    assert resp.status_code == 403
    assert "own assigned inspections" in resp.json()["detail"]
