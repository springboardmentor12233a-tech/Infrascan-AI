from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

ALLOWED_IMAGE_SOURCES = ["phone", "camera", "drone"]
ALLOWED_QUALITY_STATUSES = ["passed", "warning", "rejected"]


class Image(Base):
    __tablename__ = "images"

    image_id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(
        Integer,
        ForeignKey("inspections.inspection_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    file_path = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    width_px = Column(Integer, nullable=False)
    height_px = Column(Integer, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    source = Column(String(30), nullable=False, default="phone")
    blur_score = Column(Float, nullable=False, default=0.0)
    brightness_score = Column(Float, nullable=False, default=0.0)
    quality_status = Column(String(20), nullable=False, default="passed")
    quality_notes = Column(Text, nullable=True)
    gps_latitude = Column(Float, nullable=True)
    gps_longitude = Column(Float, nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Preprocessing pipeline fields
    processed_file_path = Column(String(255), nullable=True)
    preprocess_status = Column(String(20), nullable=False, default="not_run")
    preprocess_steps = Column(Text, nullable=True)
    preprocessed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    inspection = relationship("Inspection", back_populates="images")
    uploader = relationship("User", foreign_keys=[uploaded_by])
