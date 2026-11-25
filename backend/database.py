"""
InfraScan Database Configuration & ORM Models.

Provides SQLite persistence by default for zero-configuration local college demonstrations,
with optional PostgreSQL override via DATABASE_URL environment variable.
Supports Infrastructure Assets, Inspection Records, and Analytics.
"""

import os
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SQLITE_PATH = OUTPUTS_DIR / "infrascan.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AssetRecord(Base):
    """Stores registered infrastructure assets (bridges, buildings, roads, etc.)."""
    __tablename__ = "assets"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    asset_type = Column(String(100), nullable=False)  # Bridge, Building, Road, Pavement, Concrete Structure, Other
    location = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "asset_type": self.asset_type,
            "location": self.location,
            "description": self.description or "",
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class UserRecord(Base):
    """User account model for authentication and role-based access."""
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    full_name = Column(String(255), nullable=False, default="Inspector")
    role = Column(String(50), nullable=False, default="Inspector")  # Admin, Inspector, Engineer, Viewer
    is_active = Column(Integer, default=1)  # 1 = active, 0 = disabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class PasswordResetTokenRecord(Base):
    """Stores temporary cryptographically secure password reset tokens."""
    __tablename__ = "password_reset_tokens"

    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    token = Column(String(100), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Integer, default=0)  # 0 = unused, 1 = used
    created_at = Column(DateTime, default=datetime.utcnow)


class InspectionRecord(Base):
    """Stores full historical record of an AI crack inspection."""
    __tablename__ = "inspections"

    id = Column(String(50), primary_key=True, index=True)
    asset_id = Column(String(50), nullable=True, index=True)
    infrastructure_name = Column(String(255), nullable=False, default="Concrete Infrastructure")
    infrastructure_type = Column(String(100), nullable=False, default="Concrete Structure")
    location = Column(String(255), nullable=False, default="Site Alpha")
    inspector_name = Column(String(100), nullable=False, default="Lead Inspector")
    description = Column(Text, nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    filename = Column(String(255), nullable=False)
    image_path = Column(String(500), nullable=False)
    
    # Classification Results
    classification_label = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    crack_probability = Column(Float, nullable=False)
    
    # Segmentation Results
    segmentation_label = Column(String(50), nullable=False)
    crack_pixel_count = Column(Integer, nullable=False)
    total_pixels = Column(Integer, nullable=False)
    crack_percentage = Column(Float, nullable=False)
    
    # Damage Assessment
    severity_level = Column(String(50), nullable=False)  # None, Low, Moderate, High
    suggested_priority = Column(String(50), nullable=False, default="Normal")  # Low, Normal, High, Urgent
    
    # File storage paths
    mask_path = Column(String(500), nullable=False)
    overlay_path = Column(String(500), nullable=False)
    
    # Advisory & Summary
    summary = Column(Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id or "",
            "infrastructure_name": self.infrastructure_name or "Concrete Infrastructure",
            "infrastructure_type": self.infrastructure_type or "Concrete Structure",
            "location": self.location or "Site Alpha",
            "inspector_name": self.inspector_name or "Lead Inspector",
            "description": self.description or "",
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "filename": self.filename,
            "image_path": self.image_path,
            "classification_label": self.classification_label,
            "confidence": self.confidence,
            "crack_probability": self.crack_probability,
            "segmentation_label": self.segmentation_label,
            "crack_pixel_count": self.crack_pixel_count,
            "total_pixels": self.total_pixels,
            "crack_percentage": self.crack_percentage,
            "severity_level": self.severity_level,
            "suggested_priority": self.suggested_priority or "Normal",
            "mask_path": self.mask_path,
            "overlay_path": self.overlay_path,
            "summary": self.summary
        }


def init_db():
    """Initializes database tables, runs column migrations safely, and seeds default assets if empty."""
    Base.metadata.create_all(bind=engine)

    # Safe column additions if table already existed from previous runs
    new_cols = [
        ("asset_id", "VARCHAR(50)"),
        ("infrastructure_name", "VARCHAR(255) DEFAULT 'Concrete Infrastructure'"),
        ("infrastructure_type", "VARCHAR(100) DEFAULT 'Concrete Structure'"),
        ("location", "VARCHAR(255) DEFAULT 'Site Alpha'"),
        ("inspector_name", "VARCHAR(100) DEFAULT 'Lead Inspector'"),
        ("description", "TEXT"),
        ("suggested_priority", "VARCHAR(50) DEFAULT 'Normal'"),
    ]
    with engine.connect() as conn:
        for col_name, col_type in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE inspections ADD COLUMN {col_name} {col_type};"))
                conn.commit()
            except Exception:
                pass  # Column already exists

    # Seed initial infrastructure assets if empty
    db = SessionLocal()
    try:
        if db.query(AssetRecord).count() == 0:
            sample_assets = [
                AssetRecord(
                    id="ASSET-BRG-01",
                    name="North River Highway Viaduct",
                    asset_type="Bridge",
                    location="North Corridor, Interstate 80 Mile 44",
                    description="Prestressed reinforced concrete box girder bridge constructed in 2012."
                ),
                AssetRecord(
                    id="ASSET-ROD-02",
                    name="Eastern Expressway Pavement Section 4B",
                    asset_type="Pavement",
                    location="Eastern Bypass, KM 12+400",
                    description="Heavy traffic concrete pavement slab segment under heavy commercial axle loading."
                ),
                AssetRecord(
                    id="ASSET-WAL-03",
                    name="Westside Retaining Wall RW-14",
                    asset_type="Concrete Structure",
                    location="Hillside Cutting, Ring Road West",
                    description="Cast-in-place cantilever retaining wall stabilizing embankment slope."
                ),
                AssetRecord(
                    id="ASSET-BLD-04",
                    name="Central Transit Terminal Substructure",
                    asset_type="Building",
                    location="City Center Metro Station Level B2",
                    description="Subsurface concrete foundation columns and perimeter retaining walls."
                )
            ]
            db.add_all(sample_assets)
            db.commit()
            print("[Database] Seeded 4 reference infrastructure assets.")

        # Seed default Admin account if users table is empty
        if db.query(UserRecord).filter(UserRecord.role == "Admin").count() == 0:
            import uuid
            from backend.services.auth import hash_password
            admin_pwd = os.getenv("INFRASCAN_ADMIN_PASSWORD", "AdminPassword@123")
            admin_email = os.getenv("INFRASCAN_ADMIN_EMAIL", "admin@infrascan.ai")
            h_pwd, salt = hash_password(admin_pwd)
            admin_user = UserRecord(
                id=f"USR-{uuid.uuid4().hex[:8].upper()}",
                email=admin_email,
                hashed_password=h_pwd,
                salt=salt,
                full_name="System Administrator",
                role="Admin",
                is_active=1,
                created_at=datetime.utcnow()
            )
            db.add(admin_user)
            db.commit()
            print(f"[Database] Seeded default administrator account: {admin_email} (Password: {admin_pwd})")
    finally:
        db.close()


def get_db():
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
