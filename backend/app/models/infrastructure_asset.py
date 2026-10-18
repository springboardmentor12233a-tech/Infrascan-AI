"""
models/infrastructure_asset.py – civil infrastructure assets tracked by InfraScan.

An asset is a physical structure (bridge, building, dam, etc.) that gets
inspected over time. Latitude/longitude are plain floats for now;
PostGIS geometry columns come in Milestone 2.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    DateTime, Enum, Float, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetType(str, enum.Enum):
    """Allowed structure types. Adding a new type here also updates the DB enum."""
    BUILDING            = "Building"
    BRIDGE              = "Bridge"
    ROAD                = "Road"
    TUNNEL              = "Tunnel"
    DAM                 = "Dam"
    CONCRETE_STRUCTURE  = "Concrete Structure"
    RETAINING_WALL      = "Retaining Wall"
    INDUSTRIAL_STRUCTURE = "Industrial Structure"


class InfrastructureAsset(Base):
    __tablename__ = "infrastructure_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Human-readable unique code, e.g. "BRG-001"
    asset_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Uses the AssetType enum defined above
    type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type_enum"), nullable=False
    )

    # Free-text description of where the asset is located
    location_text: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Decimal degrees; PostGIS will replace these in Milestone 2
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Year the structure was built, e.g. 1985
    construction_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # e.g. "Reinforced Concrete", "Steel", "Masonry"
    material_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Department responsible for this asset
    responsible_department: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

    # How often (in days) this asset should be inspected; e.g. 180 = every 6 months
    inspection_frequency_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # Free-text log of past maintenance work
    maintenance_history: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    inspections: Mapped[list["Inspection"]] = relationship(  # type: ignore[name-defined]
        "Inspection", back_populates="asset"
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} code={self.asset_code!r} name={self.name!r}>"
