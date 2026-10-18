"""
Seed script to create one user per role and 3 realistic sample assets.
Run with: python seed_data.py (from backend/ directory with venv active)
"""

from app.database import SessionLocal, Base, engine
from app.models.role import Role, ROLE_NAMES
from app.models.user import User
from app.models.infrastructure_asset import InfrastructureAsset, AssetType
from app.core.security import hash_password
from app.services.seed import seed_roles

SAMPLE_USERS = [
    {
        "email": "admin@infrascan.com",
        "full_name": "System Administrator",
        "role_name": "Administrator",
        "password": "Password123!"
    },
    {
        "email": "manager@infrascan.com",
        "full_name": "Elena Vance (Manager)",
        "role_name": "Infrastructure Manager",
        "password": "Password123!"
    },
    {
        "email": "civil@infrascan.com",
        "full_name": "Dr. Marcus Brody (Civil)",
        "role_name": "Civil Engineer",
        "password": "Password123!"
    },
    {
        "email": "inspector@infrascan.com",
        "full_name": "Sarah Connor (Inspector)",
        "role_name": "Infrastructure Inspector",
        "password": "Password123!"
    },
    {
        "email": "maintenance@infrascan.com",
        "full_name": "Tom Davis (Maintenance)",
        "role_name": "Maintenance Engineer",
        "password": "Password123!"
    }
]

SAMPLE_ASSETS = [
    {
        "asset_code": "BRG-001",
        "name": "Golden Gate Overpass Viaduct",
        "type": AssetType.BRIDGE,
        "location_text": "Interstate 80, Mile Marker 42, North Bay",
        "latitude": 37.8199,
        "longitude": -122.4783,
        "construction_year": 1988,
        "material_type": "Prestressed Reinforced Concrete",
        "responsible_department": "Department of Transportation - Bridge Division",
        "inspection_frequency_days": 180,
        "maintenance_history": "2021: Expansion joint resealed. 2023: Superficial deck crack patching."
    },
    {
        "asset_code": "TUN-002",
        "name": "Metropolitan Metro East Transit Tunnel",
        "type": AssetType.TUNNEL,
        "location_text": "Underground Sector 4, Central Urban Corridor",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "construction_year": 2004,
        "material_type": "Segmental Cast Concrete Lining",
        "responsible_department": "Metropolitan Transit Authority - Structural Dept",
        "inspection_frequency_days": 90,
        "maintenance_history": "2022: Water seepage monitored at Ring 410. Grouting performed."
    },
    {
        "asset_code": "DAM-003",
        "name": "Pine Valley Reservoir Gravity Dam",
        "type": AssetType.DAM,
        "location_text": "Cascade River Canyon, Sector North",
        "latitude": 45.5152,
        "longitude": -122.6784,
        "construction_year": 1974,
        "material_type": "Mass Concrete",
        "responsible_department": "Water Resources & Dam Safety Bureau",
        "inspection_frequency_days": 365,
        "maintenance_history": "2019: Spillway resurfacing. 2024: Crest drainage cleared."
    }
]


def seed_all():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Seed Roles
        seed_roles(db)

        # 2. Seed Users
        print("Seeding sample users...")
        for u_data in SAMPLE_USERS:
            existing = db.query(User).filter(User.email == u_data["email"]).first()
            if not existing:
                role = db.query(Role).filter(Role.name == u_data["role_name"]).first()
                if role:
                    user = User(
                        email=u_data["email"],
                        full_name=u_data["full_name"],
                        password_hash=hash_password(u_data["password"]),
                        role_id=role.id,
                        is_active=True
                    )
                    db.add(user)
                    print(f"  + User created: {u_data['email']} ({u_data['role_name']})")
        db.commit()

        # 3. Seed Assets
        print("Seeding sample infrastructure assets...")
        for a_data in SAMPLE_ASSETS:
            existing = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_code == a_data["asset_code"]).first()
            if not existing:
                asset = InfrastructureAsset(**a_data)
                db.add(asset)
                print(f"  + Asset created: {a_data['asset_code']} - {a_data['name']}")
        db.commit()
        print("Seed completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
