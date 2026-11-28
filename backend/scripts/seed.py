"""
seed.py — creates demonstration data for local InfraScan development.

Usage:
    cd backend
    python scripts/seed.py

Creates:
    - 1 Admin user
    - 1 Engineer user
    - 1 Inspector user
    - 3 Infrastructure assets
    - 2 Inspections
"""

import sys
import os

# Allow running from any directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models.models import User, InfrastructureAsset, Inspection


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Users ────────────────────────────────────────────────────────────
        existing_emails = {u.email for u in db.query(User.email).all()}

        users_data = [
            {
                "full_name": "Admin User",
                "email": "admin@infrascan.io",
                "password": "adminpass123",
                "role": "Admin",
            },
            {
                "full_name": "Elena Vance",
                "email": "elena.vance@infrascan.io",
                "password": "password123",
                "role": "Engineer",
            },
            {
                "full_name": "Marcus Torres",
                "email": "marcus.torres@infrascan.io",
                "password": "password123",
                "role": "Inspector",
            },
        ]

        created_users = []
        for ud in users_data:
            if ud["email"] not in existing_emails:
                user = User(
                    full_name=ud["full_name"],
                    email=ud["email"],
                    hashed_password=hash_password(ud["password"]),
                    role=ud["role"],
                )
                db.add(user)
                created_users.append(ud["email"])

        db.commit()
        print(f"Users: created {len(created_users)}, skipped {len(users_data) - len(created_users)}")

        # ── Infrastructure Assets ────────────────────────────────────────────
        existing_codes = {a.asset_code for a in db.query(InfrastructureAsset.asset_code).all()}

        assets_data = [
            {
                "asset_code": "SEED-BRG-001",
                "name": "[DEMO] Riverside Bridge",
                "infrastructure_type": "Bridge",
                "location_name": "Riverside District, Sector 4",
                "latitude": 13.0827,
                "longitude": 80.2707,
                "construction_year": 1998,
                "material_type": "Reinforced Concrete",
                "owner": "Municipal Works Department",
            },
            {
                "asset_code": "SEED-BLD-001",
                "name": "[DEMO] Central Administration Building",
                "infrastructure_type": "Building",
                "location_name": "City Centre, Block A",
                "latitude": 13.0569,
                "longitude": 80.2425,
                "construction_year": 2005,
                "material_type": "Steel Frame + Concrete",
                "owner": "City Development Authority",
            },
            {
                "asset_code": "SEED-RWL-001",
                "name": "[DEMO] North Sector Retaining Wall",
                "infrastructure_type": "Retaining Wall",
                "location_name": "North Sector, Zone 7",
                "latitude": 13.1200,
                "longitude": 80.2890,
                "construction_year": 2012,
                "material_type": "Mass Concrete",
                "owner": "Public Works Division",
            },
        ]

        created_assets = []
        all_assets = {}
        for ad in assets_data:
            if ad["asset_code"] not in existing_codes:
                asset = InfrastructureAsset(**ad)
                db.add(asset)
                db.flush()
                all_assets[ad["asset_code"]] = asset.id
                created_assets.append(ad["asset_code"])

        db.commit()

        # Reload existing assets we might have skipped
        for a in db.query(InfrastructureAsset).all():
            if a.asset_code in {ad["asset_code"] for ad in assets_data}:
                all_assets[a.asset_code] = a.id

        print(f"Assets: created {len(created_assets)}, skipped {len(assets_data) - len(created_assets)}")

        # ── Inspections ───────────────────────────────────────────────────────
        existing_insp_codes = {i.inspection_code for i in db.query(Inspection.inspection_code).all()}

        inspections_data = [
            {
                "inspection_code": "SEED-INSP-001",
                "asset_code": "SEED-BRG-001",
                "inspection_type": "Routine Inspection",
                "inspection_date": "2026-11-20",
                "inspection_status": "Completed",
                "inspection_notes": "[DEMO] Annual structural inspection. Surface cracking observed on south pier.",
            },
            {
                "inspection_code": "SEED-INSP-002",
                "asset_code": "SEED-BLD-001",
                "inspection_type": "Special Inspection",
                "inspection_date": "2026-11-25",
                "inspection_status": "Scheduled",
                "inspection_notes": "[DEMO] Post-maintenance verification inspection.",
            },
        ]

        created_insp = []
        for id_ in inspections_data:
            if id_["inspection_code"] not in existing_insp_codes:
                asset_id = all_assets.get(id_.pop("asset_code"))
                if not asset_id:
                    continue
                inspection = Inspection(asset_id=asset_id, **id_)
                db.add(inspection)
                created_insp.append(id_["inspection_code"])

        db.commit()
        print(f"Inspections: created {len(created_insp)}, skipped {len(inspections_data) - len(created_insp)}")
        print("\nSeed complete. Demo credentials:")
        print("  Admin   : admin@infrascan.io / adminpass123")
        print("  Engineer: elena.vance@infrascan.io / password123")
        print("  Inspector: marcus.torres@infrascan.io / password123")

    finally:
        db.close()


if __name__ == "__main__":
    seed()

