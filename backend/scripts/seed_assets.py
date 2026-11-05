from pathlib import Path
import sys

# Add backend directory to sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import Base, SessionLocal, engine
from app.models.asset import InfrastructureAsset
from app.models.user import User
from app.services.audit import create_audit_log

SAMPLE_ASSETS = [
    {
        "name": "Bridge B-12",
        "asset_type": "bridge",
        "material_type": "concrete",
        "address": "Kathipara Grade Separator, Guindy, Chennai",
        "latitude": 13.0067,
        "longitude": 80.2023,
        "construction_year": 2008,
        "responsible_department": "Highways & Bridges Department",
        "inspection_frequency_days": 90,
        "importance_level": "high",
    },
    {
        "name": "Road NH-48",
        "asset_type": "road",
        "material_type": "asphalt",
        "address": "Chennai-Bengaluru Highway NH-48, Sriperumbudur Section, Chennai",
        "latitude": 12.9833,
        "longitude": 79.9500,
        "construction_year": 2012,
        "responsible_department": "National Highways Authority",
        "inspection_frequency_days": 60,
        "importance_level": "high",
    },
    {
        "name": "Tunnel T-3",
        "asset_type": "tunnel",
        "material_type": "concrete",
        "address": "Central Underground Transit Tunnel, Chennai Metro Corridor",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "construction_year": 2017,
        "responsible_department": "Metro Rail Infrastructure",
        "inspection_frequency_days": 30,
        "importance_level": "high",
    },
    {
        "name": "Building A",
        "asset_type": "building",
        "material_type": "concrete",
        "address": "Tidel Park Technical Block A, OMR Road, Taramani, Chennai",
        "latitude": 12.9892,
        "longitude": 80.2476,
        "construction_year": 2000,
        "responsible_department": "Public Works Department",
        "inspection_frequency_days": 180,
        "importance_level": "medium",
    },
    {
        "name": "Dam D-1",
        "asset_type": "dam",
        "material_type": "masonry",
        "address": "Chembarambakkam Reservoir Dam & Spillway, Chennai Outer",
        "latitude": 13.0117,
        "longitude": 80.0558,
        "construction_year": 1968,
        "responsible_department": "Water Resources Department",
        "inspection_frequency_days": 90,
        "importance_level": "high",
    },
    {
        "name": "Wall W-7",
        "asset_type": "retaining_wall",
        "material_type": "concrete",
        "address": "Ennore Coastal Protection Retaining Wall, North Chennai",
        "latitude": 13.2201,
        "longitude": 80.3255,
        "construction_year": 2015,
        "responsible_department": "Coastal Management Division",
        "inspection_frequency_days": 120,
        "importance_level": "medium",
    },
]


def seed_assets():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Find first admin or user to assign as creator
        admin = db.query(User).filter(User.role == "admin").first()
        creator_id = admin.user_id if admin else None

        seeded_count = 0
        for asset_data in SAMPLE_ASSETS:
            existing = (
                db.query(InfrastructureAsset)
                .filter(InfrastructureAsset.name == asset_data["name"])
                .first()
            )
            if existing:
                print(f"Asset '{asset_data['name']}' already exists. Skipping.")
                continue

            asset = InfrastructureAsset(
                **asset_data,
                created_by=creator_id,
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)
            seeded_count += 1

            create_audit_log(
                db=db,
                action="seed_asset",
                user_id=creator_id,
                entity_type="asset",
                entity_id=str(asset.asset_id),
            )
            print(f"Created asset #{asset.asset_id}: {asset.name} ({asset.asset_type}) at ({asset.latitude}, {asset.longitude})")

        print(f"\nSeed finished. Successfully added {seeded_count} sample asset(s).")
    finally:
        db.close()


if __name__ == "__main__":
    seed_assets()
