"""Pytest suite for Damage Map & Geospatial Endpoints (Milestone 3, Phase A / Step 7).

Verifies:
1. Coordinate and bbox validation (valid bbox filters, partial bbox or inverted bbox returns 400).
2. Severity details restricted for an unrelated inspector ('restricted' severity, None score).
3. Provisional flag behavior (True when unreviewed, False when engineer-confirmed).
4. Location fallback to asset coordinates with location_source='asset' when EXIF GPS is missing.
5. Hotspot grid aggregation (cell grouping, count, mean score, max severity).
6. Inspector routing (nearest-neighbour order, straight-line distance, 403 for unrelated inspector).
7. District filter on assets and damage endpoints.
"""

from datetime import date, datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.asset import InfrastructureAsset
from app.models.image import Image
from app.models.inspection import Inspection
from app.models.severity import SeverityAssessment
from app.models.user import User
from app.services.security import create_access_token, hash_password

TEST_DB_URL = "sqlite:///:memory:"
engine_test = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function")
def db_session():
    """Create in-memory database tables for each test."""
    Base.metadata.create_all(bind=engine_test)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def client(db_session):
    """Test client using the test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_users(db_session):
    """Seed test users: admin, engineer, inspector1, inspector2."""
    admin = User(
        full_name="Admin User",
        email="admin@infrascan.local",
        password_hash=hash_password("admin123"),
        role="admin",
    )
    engineer = User(
        full_name="Civil Engineer",
        email="engineer@infrascan.local",
        password_hash=hash_password("engineer123"),
        role="civil_engineer",
    )
    insp1 = User(
        full_name="Inspector One",
        email="insp1@infrascan.local",
        password_hash=hash_password("insp123"),
        role="inspector",
    )
    insp2 = User(
        full_name="Inspector Two",
        email="insp2@infrascan.local",
        password_hash=hash_password("insp123"),
        role="inspector",
    )
    db_session.add_all([admin, engineer, insp1, insp2])
    db_session.commit()
    for u in [admin, engineer, insp1, insp2]:
        db_session.refresh(u)
    return {"admin": admin, "engineer": engineer, "insp1": insp1, "insp2": insp2}


def auth_header(user: User) -> dict:
    token = create_access_token({"sub": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def map_seed_data(db_session, test_users):
    """Seed sample assets in multiple districts with inspections and assessments."""
    # Asset 1: Central District
    asset1 = InfrastructureAsset(
        name="Central Flyover",
        asset_type="bridge",
        material_type="concrete",
        latitude=13.0800,
        longitude=80.2700,
        district="Central",
        construction_year=2015,
        responsible_department="Highways",
        inspection_frequency_days=90,
        importance_level="high",
        created_by=test_users["admin"].user_id,
    )
    # Asset 2: North District
    asset2 = InfrastructureAsset(
        name="North Sea Wall",
        asset_type="retaining_wall",
        material_type="concrete",
        latitude=13.2000,
        longitude=80.3200,
        district="North",
        construction_year=2010,
        responsible_department="Port Trust",
        inspection_frequency_days=180,
        importance_level="medium",
        created_by=test_users["admin"].user_id,
    )
    # Asset 3: South District
    asset3 = InfrastructureAsset(
        name="South Expressway Bridge",
        asset_type="bridge",
        material_type="steel",
        latitude=12.9200,
        longitude=80.1800,
        district="South",
        construction_year=2018,
        responsible_department="Highways",
        inspection_frequency_days=90,
        importance_level="high",
        created_by=test_users["admin"].user_id,
    )
    db_session.add_all([asset1, asset2, asset3])
    db_session.commit()

    # Inspection for Asset 1 assigned to Inspector 1 (Provisional severity)
    insp1 = Inspection(
        asset_id=asset1.asset_id,
        inspector_id=test_users["insp1"].user_id,
        inspection_date=date(2026, 11, 1),
        status="completed",
    )
    # Inspection for Asset 2 assigned to Inspector 2 (Reviewed severity)
    insp2 = Inspection(
        asset_id=asset2.asset_id,
        inspector_id=test_users["insp2"].user_id,
        inspection_date=date(2026, 11, 2),
        status="completed",
    )
    # Inspection for Asset 3 assigned to Inspector 1 on the same date (for routing)
    insp3 = Inspection(
        asset_id=asset3.asset_id,
        inspector_id=test_users["insp1"].user_id,
        inspection_date=date(2026, 11, 1),
        status="completed",
    )
    db_session.add_all([insp1, insp2, insp3])
    db_session.commit()

    # Images: Image 1 has EXIF GPS; Image 2 has NO GPS (falls back to Asset 2)
    img1 = Image(
        inspection_id=insp1.inspection_id,
        uploaded_by=test_users["insp1"].user_id,
        file_path="uploads/img1.jpg",
        original_filename="img1.jpg",
        file_hash="hash1",
        width_px=1920,
        height_px=1080,
        file_size_bytes=500000,
        source="upload",
        gps_latitude=13.0815,
        gps_longitude=80.2715,
    )
    img2 = Image(
        inspection_id=insp2.inspection_id,
        uploaded_by=test_users["insp2"].user_id,
        file_path="uploads/img2.jpg",
        original_filename="img2.jpg",
        file_hash="hash2",
        width_px=1920,
        height_px=1080,
        file_size_bytes=500000,
        source="upload",
        gps_latitude=None,
        gps_longitude=None,
    )
    db_session.add_all([img1, img2])
    db_session.commit()

    # Severity assessments:
    # sa1: unreviewed (provisional = True), moderate severity
    sa1 = SeverityAssessment(
        run_id=1,
        image_id=img1.image_id,
        severity_level="moderate",
        score=45.0,
        priority_suggestion="medium",
        factors_json="[]",
        warnings_json="[]",
        rules_version="1.0.0",
        rules_sha256="dummy_sha256",
        review_status="pending",
        is_superseded=False,
    )
    # sa2: reviewed by engineer (provisional = False), critical severity
    sa2 = SeverityAssessment(
        run_id=2,
        image_id=img2.image_id,
        severity_level="severe",
        score=75.0,
        priority_suggestion="high",
        factors_json="[]",
        warnings_json="[]",
        rules_version="1.0.0",
        rules_sha256="dummy_sha256",
        review_status="reviewed",
        final_severity="critical",
        final_priority="urgent_engineering_review",
        reviewed_by=test_users["engineer"].user_id,
        reviewed_at=datetime.now(),
        is_superseded=False,
    )
    db_session.add_all([sa1, sa2])
    db_session.commit()

    return {
        "assets": [asset1, asset2, asset3],
        "inspections": [insp1, insp2, insp3],
        "images": [img1, img2],
        "assessments": [sa1, sa2],
    }


def test_bbox_validation(client, test_users, map_seed_data):
    """Test coordinate bounding box validation."""
    headers = auth_header(test_users["engineer"])

    # 1. Partial bbox returns 400
    res = client.get("/map/assets?min_lat=12.0", headers=headers)
    assert res.status_code == 400
    assert "All four bounding box coordinates" in res.json()["detail"]

    # 2. Inverted latitude returns 400
    res = client.get("/map/assets?min_lat=14.0&max_lat=12.0&min_lon=80.0&max_lon=81.0", headers=headers)
    assert res.status_code == 400
    assert "min_lat cannot be greater than max_lat" in res.json()["detail"]

    # 3. Out of bounds returns 400
    res = client.get("/map/assets?min_lat=-95.0&max_lat=12.0&min_lon=80.0&max_lon=81.0", headers=headers)
    assert res.status_code == 400
    assert "between -90 and 90" in res.json()["detail"]

    # 4. Valid bbox filters correctly
    res = client.get("/map/assets?min_lat=13.0&max_lat=13.1&min_lon=80.2&max_lon=80.3", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["features"]) == 1
    assert data["features"][0]["properties"]["name"] == "Central Flyover"


def test_inspector_severity_restriction(client, test_users, map_seed_data):
    """Inspector sees asset, but severity details only for inspections assigned to them."""
    insp1 = test_users["insp1"]
    insp2 = test_users["insp2"]
    eng = test_users["engineer"]

    # Asset 2 was inspected by Inspector 2.
    # Inspector 1 queries /map/assets: Asset 2 severity should be 'restricted'.
    res = client.get("/map/assets", headers=auth_header(insp1))
    assert res.status_code == 200
    features = {f["properties"]["name"]: f["properties"]["current_condition"] for f in res.json()["features"]}

    # Central Flyover was inspected by Inspector 1 -> full details
    assert features["Central Flyover"]["severity"] == "moderate"
    assert features["Central Flyover"]["score"] == 45.0
    assert features["Central Flyover"]["provisional"] is True

    # North Sea Wall was inspected by Inspector 2 -> restricted for Inspector 1
    assert features["North Sea Wall"]["severity"] == "restricted"
    assert features["North Sea Wall"]["score"] is None
    assert features["North Sea Wall"]["provisional"] is None

    # Civil engineer sees all severity details without restriction
    res_eng = client.get("/map/assets", headers=auth_header(eng))
    assert res_eng.status_code == 200
    features_eng = {f["properties"]["name"]: f["properties"]["current_condition"] for f in res_eng.json()["features"]}
    assert features_eng["North Sea Wall"]["severity"] == "critical"
    assert features_eng["North Sea Wall"]["provisional"] is False


def test_provisional_flag_and_reviewed_severity(client, test_users, map_seed_data):
    """Unreviewed assessment has provisional=True; reviewed has provisional=False and final_severity."""
    headers = auth_header(test_users["engineer"])
    res = client.get("/map/assets", headers=headers)
    assert res.status_code == 200
    features = {f["properties"]["name"]: f["properties"]["current_condition"] for f in res.json()["features"]}

    # Central Flyover: unreviewed -> provisional=True, severity="moderate"
    assert features["Central Flyover"]["provisional"] is True
    assert features["Central Flyover"]["severity"] == "moderate"

    # North Sea Wall: reviewed -> provisional=False, severity="critical"
    assert features["North Sea Wall"]["provisional"] is False
    assert features["North Sea Wall"]["severity"] == "critical"


def test_damage_marker_location_fallback(client, test_users, map_seed_data):
    """Damage marker uses image EXIF GPS when available, otherwise falls back to asset coordinates."""
    headers = auth_header(test_users["engineer"])
    res = client.get("/map/damage", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["features"]) == 2

    by_asset = {f["properties"]["asset_name"]: f for f in data["features"]}

    # Central Flyover image had EXIF GPS (13.0815, 80.2715)
    f1 = by_asset["Central Flyover"]
    assert f1["properties"]["location_source"] == "image_exif"
    assert f1["geometry"]["coordinates"] == [80.2715, 13.0815]

    # North Sea Wall image had no GPS -> fallback to asset (13.2000, 80.3200)
    f2 = by_asset["North Sea Wall"]
    assert f2["properties"]["location_source"] == "asset"
    assert f2["geometry"]["coordinates"] == [80.3200, 13.2000]


def test_hotspot_grid_aggregation(client, test_users, map_seed_data):
    """Hotspots endpoint groups points into grid cells and returns mean score and max severity."""
    headers = auth_header(test_users["engineer"])
    res = client.get("/map/hotspots?grid_size=0.5", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_points"] == 2
    assert len(data["grid"]) >= 1

    for cell in data["grid"]:
        assert "cell_centre" in cell
        assert cell["count"] >= 1
        assert "mean_score" in cell
        assert "max_severity" in cell


def test_district_filter(client, test_users, map_seed_data):
    """District filter isolates assets and damage to the specified district."""
    headers = auth_header(test_users["engineer"])

    # Filter district Central
    res = client.get("/map/assets?district=Central", headers=headers)
    assert res.status_code == 200
    names = [f["properties"]["name"] for f in res.json()["features"]]
    assert names == ["Central Flyover"]

    # Filter district North on damage markers
    res_dmg = client.get("/map/damage?district=North", headers=headers)
    assert res_dmg.status_code == 200
    assert len(res_dmg.json()["features"]) == 1
    assert res_dmg.json()["features"][0]["properties"]["asset_name"] == "North Sea Wall"


def test_inspector_route_nearest_neighbour_and_permissions(client, test_users, map_seed_data):
    """Test routing stops, distance calculation, and role authorization."""
    insp1 = test_users["insp1"]
    insp2 = test_users["insp2"]
    admin = test_users["admin"]

    # Inspector 1 has 2 inspections on 2026-11-01 (Asset 1 Central and Asset 3 South)
    res = client.get(f"/map/route?inspector_id={insp1.user_id}&date=2026-11-01", headers=auth_header(insp1))
    assert res.status_code == 200
    data = res.json()
    assert len(data["ordered_stops"]) == 2
    assert data["total_distance_km"] > 0
    assert data["distance_label"] == "straight-line order, not a road route"
    assert data["ordered_stops"][0]["stop_number"] == 1
    assert data["ordered_stops"][1]["stop_number"] == 2

    # Admin can view Inspector 1's route
    res_admin = client.get(f"/map/route?inspector_id={insp1.user_id}&date=2026-11-01", headers=auth_header(admin))
    assert res_admin.status_code == 200

    # Inspector 2 CANNOT view Inspector 1's route -> 403 Forbidden
    res_forbidden = client.get(f"/map/route?inspector_id={insp1.user_id}&date=2026-11-01", headers=auth_header(insp2))
    assert res_forbidden.status_code == 403
    assert "Inspectors can only view their own inspection routes" in res_forbidden.json()["detail"]


def test_map_summary(client, test_users, map_seed_data):
    """Summary endpoint groups by district with counts per severity and overdue count."""
    headers = auth_header(test_users["engineer"])
    res = client.get("/map/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_regions"] >= 3
    regions = {r["region"]: r for r in data["regions"]}

    assert "Central" in regions
    assert "North" in regions
    assert "South" in regions
    assert regions["North"]["counts_per_severity"]["critical"] == 1
