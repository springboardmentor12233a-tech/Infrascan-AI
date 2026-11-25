"""Seed Demo Assets and Data for InfraScan Map.

Ensures the interactive map has at least 10 assets with valid coordinates
around Chennai and surrounding Tamil Nadu districts.
Marks demo rows in `demo_markers` so they can be safely removed with `cleanup_demo_data.py`.
Refuses execution if more than 1,000 real assets exist.
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import Base, SessionLocal, engine
from app.models.asset import InfrastructureAsset
from app.models.demo import DemoMarker
from app.models.inspection import Inspection
from app.models.severity import InspectionSeverity
from app.models.user import User

DEMO_ASSETS = [
    {
        "name": "[DEMO] Kathipara Grade Separator B-01",
        "asset_type": "bridge",
        "material_type": "concrete",
        "address": "Kathipara Junction, Guindy, Chennai",
        "latitude": 13.0067,
        "longitude": 80.2023,
        "district": "Chennai",
        "construction_year": 2008,
        "responsible_department": "Highways Department",
        "inspection_frequency_days": 90,
        "importance_level": "high",
        "condition": "moderate",
    },
    {
        "name": "[DEMO] Napier Bridge Over Cooum",
        "asset_type": "bridge",
        "material_type": "concrete",
        "address": "Marina Beach Road, Chennai",
        "latitude": 13.0673,
        "longitude": 80.2825,
        "district": "Chennai",
        "construction_year": 1943,
        "responsible_department": "Chennai Corporation",
        "inspection_frequency_days": 60,
        "importance_level": "high",
        "condition": "minor",
    },
    {
        "name": "[DEMO] Central Metro Underground Tunnel T-02",
        "asset_type": "tunnel",
        "material_type": "concrete",
        "address": "Poonamallee High Road, Chennai Central",
        "latitude": 13.0827,
        "longitude": 80.2755,
        "district": "Chennai",
        "construction_year": 2018,
        "responsible_department": "Chennai Metro Rail Ltd",
        "inspection_frequency_days": 30,
        "importance_level": "high",
        "condition": "critical",
    },
    {
        "name": "[DEMO] Chembarambakkam Reservoir Spillway Dam",
        "asset_type": "dam",
        "material_type": "masonry",
        "address": "Chembarambakkam, Chennai Outer",
        "latitude": 13.0117,
        "longitude": 80.0558,
        "district": "Kanchipuram",
        "construction_year": 1968,
        "responsible_department": "Water Resources Department",
        "inspection_frequency_days": 90,
        "importance_level": "high",
        "condition": "severe",
    },
    {
        "name": "[DEMO] Ennore Coastal Protection Wall",
        "asset_type": "retaining_wall",
        "material_type": "concrete",
        "address": "Ennore Expressway, North Chennai",
        "latitude": 13.2201,
        "longitude": 80.3255,
        "district": "Tiruvallur",
        "construction_year": 2015,
        "responsible_department": "Public Works Department",
        "inspection_frequency_days": 120,
        "importance_level": "medium",
        "condition": "moderate",
    },
    {
        "name": "[DEMO] Rajiv Gandhi Expressway (OMR Toll Section)",
        "asset_type": "road",
        "material_type": "asphalt",
        "address": "Old Mahabalipuram Road, Perungudi, Chennai",
        "latitude": 12.9654,
        "longitude": 80.2458,
        "district": "Chengalpattu",
        "construction_year": 2011,
        "responsible_department": "Tamil Nadu Road Development Co",
        "inspection_frequency_days": 45,
        "importance_level": "high",
        "condition": "minor",
    },
    {
        "name": "[DEMO] Pamban Railway Viaduct Section 2",
        "asset_type": "bridge",
        "material_type": "concrete",
        "address": "Palk Strait Viaduct Approach",
        "latitude": 9.2825,
        "longitude": 79.1867,
        "district": "Ramanathapuram",
        "construction_year": 2020,
        "responsible_department": "Southern Railway",
        "inspection_frequency_days": 30,
        "importance_level": "high",
        "condition": "severe",
    },
    {
        "name": "[DEMO] Kallanai Grand Anicut Sluice Section",
        "asset_type": "dam",
        "material_type": "masonry",
        "address": "Grand Anicut Dam, Cauvery River Basin",
        "latitude": 10.8305,
        "longitude": 78.8188,
        "district": "Thanjavur",
        "construction_year": 1920,
        "responsible_department": "Water Resources Department",
        "inspection_frequency_days": 60,
        "importance_level": "high",
        "condition": "critical",
    },
    {
        "name": "[DEMO] Guindy Industrial Estate Technical Block",
        "asset_type": "building",
        "material_type": "concrete",
        "address": "SIDCO Industrial Estate, Guindy, Chennai",
        "latitude": 13.0102,
        "longitude": 80.2120,
        "district": "Chennai",
        "construction_year": 1995,
        "responsible_department": "SIDCO Infrastructure",
        "inspection_frequency_days": 180,
        "importance_level": "medium",
        "condition": "none",
    },
    {
        "name": "[DEMO] Sriperumbudur Industrial Corridor NH-48",
        "asset_type": "road",
        "material_type": "asphalt",
        "address": "NH-48 Corridor Km 42, Sriperumbudur",
        "latitude": 12.9833,
        "longitude": 79.9500,
        "district": "Kanchipuram",
        "construction_year": 2016,
        "responsible_department": "National Highways Authority",
        "inspection_frequency_days": 60,
        "importance_level": "high",
        "condition": "moderate",
    },
    {
        "name": "[DEMO] Maduravoyal Elevated Corridor Pillar Group 8",
        "asset_type": "bridge",
        "material_type": "concrete",
        "address": "Maduravoyal Bypass Junction, Chennai",
        "latitude": 13.0645,
        "longitude": 80.1652,
        "district": "Chennai",
        "construction_year": 2021,
        "responsible_department": "Highways Department",
        "inspection_frequency_days": 90,
        "importance_level": "high",
        "condition": "minor",
    },
    {
        "name": "[DEMO] Chengalpattu Railway Overbridge B-05",
        "asset_type": "bridge",
        "material_type": "concrete",
        "address": "GST Road Overbridge, Chengalpattu",
        "latitude": 12.6841,
        "longitude": 79.9790,
        "district": "Chengalpattu",
        "construction_year": 2014,
        "responsible_department": "Highways & Railway Liaison",
        "inspection_frequency_days": 90,
        "importance_level": "medium",
        "condition": "severe",
    },
]


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        # 1. Safety Guard: Check real assets count
        total_assets = db.query(InfrastructureAsset).count()
        if total_assets > 1000:
            print(f"[REFUSED] Database has {total_assets} assets (> 1,000 threshold). Demo seeding refused.")
            return

        # 2. Count assets with valid coordinates
        coords_count = (
            db.query(InfrastructureAsset)
            .filter(
                InfrastructureAsset.latitude.isnot(None),
                InfrastructureAsset.longitude.isnot(None),
            )
            .count()
        )
        print(f"[INFO] Current assets with coordinates: {coords_count}")

        if coords_count >= 10:
            print("[INFO] Already have 10 or more assets with coordinates. Seeding skipped.")
            return

        # 3. Find admin user for audit
        admin = db.query(User).filter(User.role == "admin").first()
        admin_id = admin.user_id if admin else None

        inspector = db.query(User).filter(User.role == "inspector").first()
        inspector_id = inspector.user_id if inspector else admin_id

        created_count = 0
        for item in DEMO_ASSETS:
            # Check if demo asset with this name already exists
            existing = db.query(InfrastructureAsset).filter(InfrastructureAsset.name == item["name"]).first()
            if existing:
                continue

            cond = item.pop("condition", "none")
            asset = InfrastructureAsset(**item, created_by=admin_id)
            db.add(asset)
            db.flush()

            # Record demo marker
            db.add(DemoMarker(entity_type="asset", entity_id=str(asset.asset_id)))

            # Create associated inspection
            insp = Inspection(
                asset_id=asset.asset_id,
                inspector_id=inspector_id,
                inspection_date=date.today() - timedelta(days=created_count * 5),
                status="completed" if cond != "none" else "assigned",
            )
            db.add(insp)
            db.flush()
            db.add(DemoMarker(entity_type="inspection", entity_id=str(insp.inspection_id)))

            # Create inspection aggregate severity
            if cond != "none":
                score_map = {"minor": 25.0, "moderate": 50.0, "severe": 75.0, "critical": 92.0}
                insp_sev = InspectionSeverity(
                    inspection_id=insp.inspection_id,
                    worst_severity=cond,
                    worst_score=score_map.get(cond, 20.0),
                    images_assessed=3,
                    images_pending_review=1 if cond in ("moderate", "severe") else 0,
                )
                db.add(insp_sev)
                db.flush()
                db.add(DemoMarker(entity_type="inspection_severity", entity_id=str(insp_sev.id)))

            created_count += 1

        db.commit()
        print(f"[SUCCESS] Created {created_count} demo infrastructure assets with coordinates around Chennai.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to seed demo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
