"""SQLAlchemy model for explainable AI (XAI) attention maps and explanations."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Explanation(Base):
    __tablename__ = "explanations"

    explanation_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    image_id = Column(Integer, ForeignKey("images.image_id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(String(100), nullable=False, index=True)
    method = Column(String(50), nullable=False)  # "gradcam", "gradcampp", "eigencam", "saliency"
    target = Column(String(50), nullable=False)  # "mask", "detections"
    heatmap_path = Column(String(255), nullable=True)  # Path to saved .npy or 16-bit PNG
    overlay_path = Column(String(255), nullable=True)  # Path to saved JET-blended overlay PNG
    params_json = Column(Text, nullable=True)          # JSON serialized parameters and layer metadata
    warnings_json = Column(Text, nullable=True)        # JSON serialized warnings (e.g. fallback used)
    seconds = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="done")  # "done", "failed"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    run = relationship("AnalysisRun", backref="explanations", passive_deletes=True)
    image = relationship("Image", backref="explanations", passive_deletes=True)
