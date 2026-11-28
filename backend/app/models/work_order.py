"""
models/work_order.py – Maintenance work orders generated from defect findings.
"""
import enum
from datetime import datetime, date
from sqlalchemy import (
    DateTime, Date, Enum, Float, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class WorkOrderStatus(str, enum.Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CANCELLED = "Cancelled"


class WorkOrderPriority(str, enum.Enum):
    ROUTINE = "Routine Monitoring"
    LOW = "Low Priority"
    MEDIUM = "Medium Priority"
    HIGH = "High Priority"
    CRITICAL = "Urgent Engineering Review"


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("infrastructure_assets.id"), nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("inspections.id"), nullable=True)
    assigned_to_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[WorkOrderPriority] = mapped_column(
        Enum(WorkOrderPriority, name="work_order_priority_enum"),
        default=WorkOrderPriority.MEDIUM,
        nullable=False
    )
    status: Mapped[WorkOrderStatus] = mapped_column(
        Enum(WorkOrderStatus, name="work_order_status_enum"),
        default=WorkOrderStatus.OPEN,
        nullable=False
    )
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    asset: Mapped["InfrastructureAsset"] = relationship("InfrastructureAsset")  # type: ignore[name-defined]
    inspection: Mapped["Inspection | None"] = relationship("Inspection")         # type: ignore[name-defined]
    assigned_to: Mapped["User | None"] = relationship("User")                   # type: ignore[name-defined]
