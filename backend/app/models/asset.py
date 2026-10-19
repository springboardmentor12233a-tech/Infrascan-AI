from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# Allowed domain values for infrastructure assets
ALLOWED_ASSET_TYPES = [
    "building",
    "bridge",
    "road",
    "tunnel",
    "dam",
    "concrete_structure",
    "retaining_wall",
    "industrial",
]

ALLOWED_MATERIAL_TYPES = [
    "concrete",
    "asphalt",
    "steel",
    "masonry",
    "other",
]

ALLOWED_IMPORTANCE_LEVELS = [
    "low",
    "medium",
    "high",
]


class InfrastructureAsset(Base):
    __tablename__ = "infrastructure_assets"

    asset_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False, index=True)
    material_type = Column(String(50), nullable=False, index=True)
    address = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    construction_year = Column(Integer, nullable=False)
    responsible_department = Column(String(100), nullable=False)
    inspection_frequency_days = Column(Integer, nullable=False)
    importance_level = Column(String(20), nullable=False)
    created_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    inspections = relationship("Inspection", back_populates="asset", cascade="all, delete-orphan")
