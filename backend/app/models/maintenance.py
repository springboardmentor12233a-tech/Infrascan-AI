from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


ALLOWED_MAINTENANCE_PRIORITIES = [
    "routine_monitoring",
    "low",
    "medium",
    "high",
    "urgent_engineering_review",
]

ALLOWED_MAINTENANCE_STATUSES = [
    "pending",
    "scheduled",
    "in_progress",
    "completed",
]


class MaintenanceRecommendation(Base):
    __tablename__ = "maintenance_recommendations"
    __table_args__ = {"extend_existing": True}

    recommendation_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.asset_id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.inspection_id", ondelete="SET NULL"), nullable=True, index=True)

    priority = Column(String(50), nullable=False, default="medium")
    action_required = Column(String(500), nullable=False)
    recommended_technique = Column(String(255), nullable=True)
    estimated_cost_tier = Column(String(20), nullable=False, default="medium")  # low, medium, high
    urgency_days = Column(Integer, nullable=False, default=30)
    status = Column(String(30), nullable=False, default="pending")
    assigned_to = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    asset = relationship("InfrastructureAsset", backref="maintenance_recommendations")
    inspection = relationship("Inspection", backref="maintenance_recommendations")
