from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


ALLOWED_DEFECT_TYPES = [
    "longitudinal_crack",
    "transverse_crack",
    "alligator_crack",
    "diagonal_crack",
    "pothole",
    "concrete_spalling",
    "exposed_rebar",
    "corrosion",
    "water_staining",
    "surface_erosion",
]

ALLOWED_SEVERITY_LEVELS = [
    "no_damage",
    "minor",
    "moderate",
    "severe",
    "critical",
]


class DamageAssessment(Base):
    __tablename__ = "damage_assessments"
    __table_args__ = {"extend_existing": True}

    assessment_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("images.image_id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.inspection_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Classification / Detection
    defect_type = Column(String(50), nullable=False, default="longitudinal_crack")
    confidence = Column(Float, nullable=False, default=0.0)
    bounding_box = Column(Text, nullable=True)  # JSON-encoded coordinates: {"x1":.., "y1":.., "x2":.., "y2":..}
    
    # Segmentation & XAI outputs
    mask_path = Column(String(500), nullable=True)
    heatmap_path = Column(String(500), nullable=True)  # Grad-CAM heatmap path
    
    # Geometric Measurements
    crack_length_px = Column(Float, nullable=True, default=0.0)
    avg_width_px = Column(Float, nullable=True, default=0.0)
    max_width_px = Column(Float, nullable=True, default=0.0)
    crack_area_px = Column(Float, nullable=True, default=0.0)
    crack_density_pct = Column(Float, nullable=True, default=0.0)
    orientation_degrees = Column(Float, nullable=True, default=0.0)
    
    # Real-world calibrated estimates (mm) if scale factor is known
    estimated_length_mm = Column(Float, nullable=True)
    estimated_max_width_mm = Column(Float, nullable=True)
    scale_calibration_mm_per_px = Column(Float, nullable=True)

    # Severity Assessment
    severity_category = Column(String(30), nullable=False, default="minor")
    severity_score = Column(Float, nullable=False, default=0.0)  # 0 to 100
    engineering_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    image = relationship("Image", backref="damage_assessments")
    inspection = relationship("Inspection", backref="damage_assessments")
