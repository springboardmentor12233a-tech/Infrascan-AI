"""SQLAlchemy models for damage severity assessment."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SeverityAssessment(Base):
    __tablename__ = "severity_assessments"

    assessment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    image_id = Column(Integer, ForeignKey("images.image_id", ondelete="CASCADE"), nullable=False, index=True)
    severity_level = Column(String(50), nullable=False)  # none, minor, moderate, severe, critical
    score = Column(Float, nullable=False)
    priority_suggestion = Column(String(50), nullable=False)
    factors_json = Column(Text, nullable=False)
    warnings_json = Column(Text, nullable=True)
    rules_version = Column(String(50), nullable=False)
    rules_sha256 = Column(String(64), nullable=False)
    review_status = Column(String(50), nullable=False, default="pending")  # pending, confirmed, corrected
    reviewed_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    final_severity = Column(String(50), nullable=True)
    final_priority = Column(String(50), nullable=True)
    review_comment = Column(Text, nullable=True)
    is_superseded = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    run = relationship("AnalysisRun")
    image = relationship("Image")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class InspectionSeverity(Base):
    __tablename__ = "inspection_severity"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("inspections.inspection_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    worst_severity = Column(String(50), nullable=False, default="none")
    worst_score = Column(Float, nullable=False, default=0.0)
    images_assessed = Column(Integer, nullable=False, default=0)
    images_pending_review = Column(Integer, nullable=False, default=0)
    summary_json = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    inspection = relationship("Inspection")

