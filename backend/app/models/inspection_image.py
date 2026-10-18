"""
models/inspection_image.py – an image uploaded during an inspection.

Each image record stores:
  - where the file is saved on disk
  - image dimensions and size
  - quality metrics (blur score, brightness)
  - an MD5 hash so we can detect exact duplicates
  - a quality_status flag so the frontend can show a badge
"""

import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class QualityStatus(str, enum.Enum):
    OK         = "ok"
    BLURRY     = "blurry"
    LOW_LIGHT  = "low_light"


class InspectionImage(Base):
    __tablename__ = "inspection_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Which inspection this image belongs to
    inspection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inspections.id"), nullable=False, index=True
    )

    # Safe random filename we generated (e.g. "abc123.jpg") – NOT the user's filename
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Original filename the user uploaded – kept for display purposes only
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # MD5 of the file bytes – used to reject exact duplicates within an inspection
    md5_hash: Mapped[str] = mapped_column(String(32), nullable=False)

    # Image dimensions in pixels
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)

    # File size in kilobytes
    file_size_kb: Mapped[float] = mapped_column(Float, nullable=False)

    # Variance of Laplacian – measures how sharp the image is
    # Low value → blurry image
    blur_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Mean gray-level brightness (0=black, 255=white)
    # Low value → dark / low-light image
    brightness: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Final quality verdict used for the badge on the frontend
    quality_status: Mapped[QualityStatus] = mapped_column(
        Enum(QualityStatus, name="quality_status_enum"),
        default=QualityStatus.OK,
        nullable=False,
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    inspection: Mapped["Inspection"] = relationship(  # type: ignore[name-defined]
        "Inspection", back_populates="images"
    )

    def __repr__(self) -> str:
        return (
            f"<InspectionImage id={self.id} "
            f"inspection_id={self.inspection_id} "
            f"quality={self.quality_status.value!r}>"
        )
