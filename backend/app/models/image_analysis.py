"""Saved result of one AI analysis run for an inspection image."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ImageAnalysis(Base):
    __tablename__ = "image_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    image_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inspection_images.id"), nullable=False, unique=True, index=True
    )

    quality_json: Mapped[str] = mapped_column(Text, nullable=False)
    classification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    classification_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification_json: Mapped[str] = mapped_column(Text, nullable=False)

    detection_status: Mapped[str] = mapped_column(String(32), nullable=False)
    detection_json: Mapped[str] = mapped_column(Text, nullable=False)

    segmentation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    segmentation_json: Mapped[str] = mapped_column(Text, nullable=False)
    mask_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    overlay_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    geometry_json: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    image: Mapped["InspectionImage"] = relationship("InspectionImage")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<ImageAnalysis id={self.id} image_id={self.image_id}>"
