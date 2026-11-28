import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(40), default="Viewer", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class InfrastructureAsset(Base):
    __tablename__ = "infrastructure_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    asset_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    infrastructure_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    construction_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    material_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(150), nullable=True)
    asset_status: Mapped[str] = mapped_column(String(40), default="Active", index=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    inspections: Mapped[list["Inspection"]] = relationship("Inspection", back_populates="asset")


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    inspection_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("infrastructure_assets.id"), nullable=False, index=True)
    inspection_type: Mapped[str] = mapped_column(String(60), default="Routine Inspection")
    inspection_date: Mapped[str] = mapped_column(String(30), nullable=False)
    inspector_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    weather_conditions: Mapped[str | None] = mapped_column(String(100), nullable=True)
    environmental_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    inspection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    inspection_status: Mapped[str] = mapped_column(String(40), default="Scheduled", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    asset: Mapped["InfrastructureAsset"] = relationship("InfrastructureAsset", back_populates="inspections")


class ImageRecord(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    image_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("infrastructure_assets.id"), nullable=False, index=True)
    inspection_id: Mapped[str] = mapped_column(String(36), ForeignKey("inspections.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calibration_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_quality_status: Mapped[str] = mapped_column(String(40), default="Requires Review")
    uploaded_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    analysis_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("infrastructure_assets.id"), nullable=False, index=True)
    inspection_id: Mapped[str] = mapped_column(String(36), ForeignKey("inspections.id"), nullable=False, index=True)
    image_id: Mapped[str] = mapped_column(String(36), ForeignKey("images.id"), nullable=False, index=True)
    pipeline_type: Mapped[str] = mapped_column(String(80), nullable=False)
    selected_models: Mapped[list] = mapped_column(JSON, default=list)
    configuration: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    job_status: Mapped[str] = mapped_column(String(40), default="Queued", index=True)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    model_type: Mapped[str] = mapped_column(String(60), nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    framework: Mapped[str] = mapped_column(String(40), default="PyTorch")
    weights_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DamageFinding(Base):
    __tablename__ = "damage_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_jobs.id"), nullable=False, index=True)
    image_id: Mapped[str] = mapped_column(String(36), ForeignKey("images.id"), nullable=False, index=True)
    damage_category: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounding_box: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    segmentation_mask_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    geometric_measurements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_severity: Mapped[str] = mapped_column(String(40), default="Pending")
    review_status: Mapped[str] = mapped_column(String(40), default="Pending Review", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class EngineerReview(Base):
    __tablename__ = "engineer_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("damage_findings.id"), nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    review_decision: Mapped[str] = mapped_column(String(40), nullable=False)
    corrected_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    corrected_severity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    engineering_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    image_id: Mapped[str] = mapped_column(String(36), ForeignKey("images.id"), nullable=False, index=True)
    finding_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("damage_findings.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    annotation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    annotation_geometry: Mapped[dict] = mapped_column(JSON, nullable=False)
    annotation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    report_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("infrastructure_assets.id"), nullable=False, index=True)
    inspection_id: Mapped[str] = mapped_column(String(36), ForeignKey("inspections.id"), nullable=False, index=True)
    analysis_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("analysis_jobs.id"), nullable=True)
    report_type: Mapped[str] = mapped_column(String(60), default="Inspection Summary")
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

