import io
import json
import os
import zipfile
from datetime import datetime, timezone
import jsonschema
from openpyxl import load_workbook
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.analysis import AnalysisRun, CrackMeasurement, Detection, ImageScale
from app.models.asset import InfrastructureAsset
from app.models.image import Image
from app.models.inspection import Inspection
from app.models.maintenance import MaintenanceTask
from app.models.report import Report, ReportFile
from app.models.severity import InspectionSeverity, SeverityAssessment
from app.models.user import User
from app.services.report_service import SCHEMA_PATH, sanitize_csv_cell
from app.services.security import create_access_token, hash_password

# In-memory SQLite for testing
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


def make_auth_headers(user: User) -> dict:
    token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.user_id})
    return {"Authorization": f"Bearer {token}"}


def setup_sample_inspection(db, inspector: User, review_status: str = "unreviewed"):
    asset = InfrastructureAsset(
        name="=Test Bridge #1",
        asset_type="bridge",
        material_type="concrete",
        address="@123 Highway Ave",
        latitude=37.7749,
        longitude=-122.4194,
        construction_year=1998,
        responsible_department="DOT",
        inspection_frequency_days=365,
        importance_level="high",
        district="District 4",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    inspection = Inspection(
        asset_id=asset.asset_id,
        inspector_id=inspector.user_id,
        inspection_date=datetime.now(timezone.utc),
        status="completed",
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    image = Image(
        inspection_id=inspection.inspection_id,
        file_path="storage/images/nonexistent_sample.jpg",
        original_filename="nonexistent_sample.jpg",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        width_px=1000,
        height_px=1000,
        file_size_bytes=1024,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    analysis = AnalysisRun(
        image_id=image.image_id,
        status="done",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    detection = Detection(
        run_id=analysis.run_id,
        damage_type="crack",
        damage_label="Crack",
        confidence=0.91,
        x_min=10.0,
        y_min=10.0,
        x_max=100.0,
        y_max=100.0,
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)

    measurement = CrackMeasurement(
        run_id=analysis.run_id,
        mask_path="storage/masks/sample.png",
        length_px=150.0,
        avg_width_px=4.2,
        max_width_px=8.5,
        orientation_deg=45.0,
        length_mm=30.0,
        avg_width_mm=0.84,
        max_width_mm=1.7,
    )
    db.add(measurement)

    scale = ImageScale(
        image_id=image.image_id,
        method="reference_object",
        mm_per_pixel=0.2,
        uncertainty_percent=2.5,
        is_current=True,
    )
    db.add(scale)

    severity_assess = SeverityAssessment(
        run_id=analysis.run_id,
        image_id=image.image_id,
        severity_level="high",
        score=0.82,
        priority_suggestion="P1",
        factors_json=json.dumps({"width": 1.7, "length": 30.0}),
        rules_version="v1.0",
        rules_sha256="d04b6118b31a89c8a9840c9d74e892c9028919a3bb9f79883bb175e14b13a35a",
        review_status=review_status,
    )
    db.add(severity_assess)

    insp_severity = InspectionSeverity(
        inspection_id=inspection.inspection_id,
        worst_severity="high",
        worst_score=0.82,
        images_assessed=1,
        images_pending_review=(1 if review_status == "pending" else 0),
        summary_json="{}",
    )
    db.add(insp_severity)

    task = MaintenanceTask(
        asset_id=asset.asset_id,
        inspection_id=inspection.inspection_id,
        title="Repair crack on Pier 2",
        description="Epoxy injection required",
        task_type="repair",
        priority="P2",
        status="open",
    )
    db.add(task)

    db.commit()
    return asset, inspection, image


def test_create_and_download_report_draft(client: TestClient, db_session):
    inspector = User(
        full_name="Inspector Alice",
        email="alice@example.com",
        password_hash=hash_password("Password123!"),
        role="inspector",
        is_active=True,
    )
    db_session.add(inspector)
    db_session.commit()
    db_session.refresh(inspector)

    asset, inspection, image = setup_sample_inspection(db_session, inspector, review_status="unreviewed")
    headers = make_auth_headers(inspector)

    # 1. POST /inspections/{id}/reports
    resp = client.post(
        f"/inspections/{inspection.inspection_id}/reports",
        json={"notes": "Preliminary field inspection report"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["inspection_id"] == inspection.inspection_id
    assert data["status"] == "draft"
    assert data["version"] == 1
    report_id = data["report_id"]
    assert len(data["files"]) == 4

    # 2. Verify JSON snapshot schema
    with open(SCHEMA_PATH, "r") as f:
        schema = json.load(f)

    # Fetch report details
    get_resp = client.get(f"/reports/{report_id}", headers=headers)
    assert get_resp.status_code == 200
    report_detail = get_resp.json()
    assert report_detail["report_id"] == report_id

    # 3. Test downloads
    # PDF
    pdf_resp = client.get(f"/reports/{report_id}/download?format=pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 1000

    # CSV Zip Bundle
    csv_resp = client.get(f"/reports/{report_id}/download?format=csv", headers=headers)
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(csv_resp.content)) as z:
        names = z.namelist()
        assert "summary.csv" in names
        assert "images.csv" in names
        assert "detections.csv" in names
        assert "measurements.csv" in names
        assert "severity.csv" in names
        assert "maintenance.csv" in names

        # Check CSV formula injection protection: "=Test Bridge #1" -> "'=Test Bridge #1"
        summary_txt = z.read("summary.csv").decode("utf-8")
        assert "'=Test Bridge #1" in summary_txt

    # Excel
    xlsx_resp = client.get(f"/reports/{report_id}/download?format=xlsx", headers=headers)
    assert xlsx_resp.status_code == 200
    wb = load_workbook(io.BytesIO(xlsx_resp.content))
    expected_sheets = ["README", "Summary", "Images", "Detections", "Measurements", "Severity", "Maintenance", "Models"]
    for s in expected_sheets:
        assert s in wb.sheetnames
    readme_texts = [str(cell.value) for row in wb["README"].iter_rows() for cell in row if cell.value]
    assert any("AI result for engineer review, not a final structural safety verdict." in t for t in readme_texts)

    # JSON
    json_resp = client.get(f"/reports/{report_id}/download?format=json", headers=headers)
    assert json_resp.status_code == 200
    snapshot_data = json_resp.json()
    jsonschema.validate(instance=snapshot_data, schema=schema)
    assert snapshot_data["status"] == "draft"
    assert snapshot_data["asset"]["name"] == "=Test Bridge #1"


def test_final_report_when_approved(client: TestClient, db_session):
    engineer = User(
        full_name="Engineer Bob",
        email="bob@example.com",
        password_hash=hash_password("Password123!"),
        role="civil_engineer",
        is_active=True,
    )
    db_session.add(engineer)
    db_session.commit()
    db_session.refresh(engineer)

    asset, inspection, image = setup_sample_inspection(db_session, engineer, review_status="approved")
    headers = make_auth_headers(engineer)

    resp = client.post(
        f"/inspections/{inspection.inspection_id}/reports",
        json={"notes": "Final approved inspection report"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "final"
    assert data["is_final"] is True


def test_report_access_control(client: TestClient, db_session):
    inspector1 = User(
        full_name="Inspector 1",
        email="insp1@example.com",
        password_hash=hash_password("Password123!"),
        role="inspector",
        is_active=True,
    )
    inspector2 = User(
        full_name="Inspector 2",
        email="insp2@example.com",
        password_hash=hash_password("Password123!"),
        role="inspector",
        is_active=True,
    )
    admin = User(
        full_name="Admin User",
        email="admin@example.com",
        password_hash=hash_password("Password123!"),
        role="admin",
        is_active=True,
    )
    db_session.add_all([inspector1, inspector2, admin])
    db_session.commit()

    asset, inspection, image = setup_sample_inspection(db_session, inspector1)

    headers1 = make_auth_headers(inspector1)
    headers2 = make_auth_headers(inspector2)
    headers_admin = make_auth_headers(admin)

    # Inspector 1 can create report
    resp1 = client.post(f"/inspections/{inspection.inspection_id}/reports", headers=headers1)
    assert resp1.status_code == 201
    report_id = resp1.json()["report_id"]

    # Inspector 2 cannot create report for inspection 1 (403 Forbidden)
    resp2 = client.post(f"/inspections/{inspection.inspection_id}/reports", headers=headers2)
    assert resp2.status_code == 403

    # Inspector 2 cannot get report details or download
    assert client.get(f"/reports/{report_id}", headers=headers2).status_code == 403
    assert client.get(f"/reports/{report_id}/download?format=pdf", headers=headers2).status_code == 403

    # Admin can get report details and download
    assert client.get(f"/reports/{report_id}", headers=headers_admin).status_code == 200
    assert client.get(f"/reports/{report_id}/download?format=pdf", headers=headers_admin).status_code == 200


def test_asset_and_portfolio_exports(client: TestClient, db_session):
    engineer = User(
        full_name="Chief Engineer",
        email="chief@example.com",
        password_hash=hash_password("Password123!"),
        role="civil_engineer",
        is_active=True,
    )
    db_session.add(engineer)
    db_session.commit()

    asset, inspection, image = setup_sample_inspection(db_session, engineer)
    headers = make_auth_headers(engineer)

    # Asset Export CSV
    resp_csv = client.get(f"/assets/{asset.asset_id}/export?format=csv", headers=headers)
    assert resp_csv.status_code == 200
    assert resp_csv.headers["content-type"] == "text/csv; charset=utf-8"
    assert "AI result for engineer review, not a final structural safety verdict." in resp_csv.text
    assert "'=Test Bridge #1" in resp_csv.text

    # Asset Export XLSX
    resp_xlsx = client.get(f"/assets/{asset.asset_id}/export?format=xlsx", headers=headers)
    assert resp_xlsx.status_code == 200
    wb_asset = load_workbook(io.BytesIO(resp_xlsx.content))
    assert "Asset Summary" in wb_asset.sheetnames

    # Portfolio Export CSV
    resp_port_csv = client.get("/exports/portfolio?format=csv", headers=headers)
    assert resp_port_csv.status_code == 200
    assert "AI result for engineer review, not a final structural safety verdict." in resp_port_csv.text
    assert "Portfolio Summary" in resp_port_csv.text

    # Portfolio Export XLSX
    resp_port_xlsx = client.get("/exports/portfolio?format=xlsx", headers=headers)
    assert resp_port_xlsx.status_code == 200
    wb_port = load_workbook(io.BytesIO(resp_port_xlsx.content))
    assert "Portfolio Summary" in wb_port.sheetnames


def test_sanitize_csv_cell():
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd") == "'+cmd"
    assert sanitize_csv_cell("-5") == "'-5"
    assert sanitize_csv_cell("@SUM") == "'@SUM"
    assert sanitize_csv_cell("Normal Text") == "Normal Text"
    assert sanitize_csv_cell(None) == ""
    assert sanitize_csv_cell(123) == "123"
