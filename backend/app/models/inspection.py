from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import func
from ..db import Base

# Allowed inspection statuses
ALLOWED_INSPECTION_STATUSES = [
    "assigned",
    "in_progress",
    "completed",
    "reviewed",
]


class Inspection(Base):
    __tablename__ = "inspections"

    inspection_id = Column(Integer, primary_key=True, index=True)
    id = synonym("inspection_id")
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.asset_id", ondelete="CASCADE"), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    inspection_date = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="assigned")
    notes = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    asset = relationship("InfrastructureAsset", back_populates="inspections")
    inspector = relationship("User", foreign_keys=[inspector_id])
    images = relationship("Image", back_populates="inspection", cascade="all, delete-orphan")
