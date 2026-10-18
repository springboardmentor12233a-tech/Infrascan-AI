"""
models/inspection.py – an inspection event on an asset.

An inspection is created when an inspector visits a site.
It goes through these statuses:
  pending → in_progress → completed
"""

import enum
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InspectionStatus(str, enum.Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Which asset is being inspected
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("infrastructure_assets.id"), nullable=False, index=True
    )

    # Which user (inspector) is doing the inspection
    inspector_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    # The date when the inspection takes/took place
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[InspectionStatus] = mapped_column(
        Enum(InspectionStatus, name="inspection_status_enum"),
        default=InspectionStatus.PENDING,
        nullable=False,
    )

    # Optional field notes from the inspector
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    asset: Mapped["InfrastructureAsset"] = relationship(  # type: ignore[name-defined]
        "InfrastructureAsset", back_populates="inspections"
    )
    inspector: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="inspections", foreign_keys=[inspector_id]
    )
    images: Mapped[list["InspectionImage"]] = relationship(  # type: ignore[name-defined]
        "InspectionImage", back_populates="inspection"
    )

    def __repr__(self) -> str:
        return (
            f"<Inspection id={self.id} asset_id={self.asset_id} "
            f"status={self.status.value!r}>"
        )
