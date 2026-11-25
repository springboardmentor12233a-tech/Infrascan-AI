"""SQLAlchemy models for AI model versions, analysis runs, detections, and crack measurements."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# Association table for analysis_runs and model_versions
run_models = Table(
    "run_models",
    Base.metadata,
    Column("run_id", Integer, ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), primary_key=True),
    Column("model_id", String(100), ForeignKey("model_versions.model_id", ondelete="CASCADE"), primary_key=True),
)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    model_id = Column(String(100), primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    task = Column(String(50), nullable=False)  # "detection" or "segmentation"
    version = Column(String(50), nullable=False, default="1.0")
    weights_path = Column(String(255), nullable=False)
    threshold = Column(Float, nullable=False, default=0.25)
    class_names_json = Column(Text, nullable=True)
    metrics_json = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    inferences_count = Column(Integer, nullable=False, default=0)
    mean_inference_time_ms = Column(Float, nullable=False, default=0.0)
    last_inference_at = Column(DateTime(timezone=True), nullable=True)
    error_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    run_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("images.image_id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")  # "pending", "done", "failed"
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    seconds = Column(Float, nullable=True)
    image_scale_note = Column(Text, nullable=True)

    # Relationships
    image = relationship("Image", foreign_keys=[image_id])
    detections = relationship("Detection", back_populates="run", cascade="all, delete-orphan")
    crack_measurements = relationship("CrackMeasurement", back_populates="run", cascade="all, delete-orphan")
    models = relationship("ModelVersion", secondary=run_models, backref="runs")


class Detection(Base):
    __tablename__ = "detections"

    detection_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(String(100), ForeignKey("model_versions.model_id", ondelete="SET NULL"), nullable=True, index=True)
    damage_type = Column(String(50), nullable=False)
    damage_label = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    x_min = Column(Float, nullable=False)
    y_min = Column(Float, nullable=False)
    x_max = Column(Float, nullable=False)
    y_max = Column(Float, nullable=False)

    # Relationships
    run = relationship("AnalysisRun", back_populates="detections")
    model = relationship("ModelVersion")


class CrackMeasurement(Base):
    __tablename__ = "crack_measurements"

    measurement_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    mask_path = Column(String(255), nullable=False)
    threshold = Column(Float, nullable=False, default=0.40)
    crack_pixels = Column(Integer, nullable=False, default=0)
    length_px = Column(Float, nullable=False, default=0.0)
    avg_width_px = Column(Float, nullable=False, default=0.0)
    max_width_px = Column(Float, nullable=False, default=0.0)
    p95_width_px = Column(Float, nullable=False, default=0.0)
    area_px = Column(Integer, nullable=False, default=0)
    density_percent = Column(Float, nullable=False, default=0.0)
    orientation_deg = Column(Float, nullable=False, default=0.0)
    num_components = Column(Integer, nullable=False, default=0)
    num_branch_points = Column(Integer, nullable=False, default=0)
    num_end_points = Column(Integer, nullable=False, default=0)
    mm_per_pixel = Column(Float, nullable=True)
    length_mm = Column(Float, nullable=True)
    avg_width_mm = Column(Float, nullable=True)
    max_width_mm = Column(Float, nullable=True)
    width_mode = Column(String(30), nullable=False, default="edt2")
    scale_id = Column(Integer, ForeignKey("image_scales.scale_id", ondelete="SET NULL"), nullable=True)
    length_mm_uncertainty = Column(Float, nullable=True)
    width_mm_uncertainty = Column(Float, nullable=True)
    measurement_note = Column(Text, nullable=True)

    # Relationships
    run = relationship("AnalysisRun", back_populates="crack_measurements")
    scale = relationship("ImageScale")


class ImageScale(Base):
    __tablename__ = "image_scales"

    scale_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("images.image_id", ondelete="CASCADE"), nullable=False, index=True)
    method = Column(String(30), nullable=False)  # "manual_ratio" or "reference_object"
    mm_per_pixel = Column(Float, nullable=False)
    reference_mm = Column(Float, nullable=True)
    reference_px = Column(Float, nullable=True)
    point1_x = Column(Float, nullable=True)
    point1_y = Column(Float, nullable=True)
    point2_x = Column(Float, nullable=True)
    point2_y = Column(Float, nullable=True)
    camera_perpendicular = Column(Boolean, nullable=False, default=True)
    uncertainty_percent = Column(Float, nullable=False, default=0.0)
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    set_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    image = relationship("Image", back_populates="scales")
    setter = relationship("User", foreign_keys=[set_by])


