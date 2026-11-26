import sys, os
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default="user", nullable=False)  # "user" or "admin"
    status = Column(String(20), default="active", nullable=False)  # "active" or "inactive"
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    inspections = relationship("Inspection", back_populates="user")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # Bridge, Building, Road, Tunnel, Dam, Concrete Structure
    location_name = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    construction_year = Column(Integer, nullable=True)
    material_type = Column(String(50), default="Reinforced Concrete")
    responsible_dept = Column(String(100), default="Infrastructure Maintenance")
    created_at = Column(DateTime, default=datetime.utcnow)

    inspections = relationship("Inspection", back_populates="asset", cascade="all, delete-orphan")

class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    image_filename = Column(String(255), nullable=False)
    original_image_path = Column(String(500), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    inspector_name = Column(String(100), default="Civil Engineer Inspector")
    notes = Column(Text, nullable=True)
    
    # Location data
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_source = Column(String(50), default="manual")  # exif, manual, asset_default, none

    asset = relationship("Asset", back_populates="inspections")
    user = relationship("User", back_populates="inspections")
    results = relationship("InspectionResult", back_populates="inspection", uselist=False, cascade="all, delete-orphan")

class InspectionResult(Base):
    __tablename__ = "inspection_results"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False, unique=True)
    
    # Classification
    crack_detected = Column(Boolean, default=False)
    crack_probability = Column(Float, default=0.0)
    surface_type = Column(String(50), default="Unknown")
    classification_notes = Column(String(255), default="")

    # Object Detection (Crack bounding boxes)
    defect_count = Column(Integer, default=0)
    detections_json = Column(Text, default="[]")  # [{box: [x1, y1, x2, y2], conf: 0.85, class: 'crack'}]

    # Segmentation
    mask_image_path = Column(String(500), nullable=True)
    overlay_image_path = Column(String(500), nullable=True)
    crack_area_px = Column(Integer, default=0)
    crack_area_ratio = Column(Float, default=0.0)  # percentage of inspected surface

    # Geometry & Measurements (Uncalibrated pixel metrics)
    skeleton_length_px = Column(Float, default=0.0)
    mean_width_px = Column(Float, default=0.0)
    max_width_px = Column(Float, default=0.0)
    crack_density = Column(Float, default=0.0)
    orientation_angle = Column(Float, default=0.0)
    num_branches = Column(Integer, default=0)
    num_components = Column(Integer, default=0)
    
    # Calibration metadata
    is_calibrated = Column(Boolean, default=False)
    scale_mm_per_px = Column(Float, nullable=True)
    estimated_length_mm = Column(Float, nullable=True)
    estimated_max_width_mm = Column(Float, nullable=True)

    # Damage Severity
    severity_level = Column(String(50), default="No Visible Damage")  # Minor, Moderate, Severe, Critical
    severity_score = Column(Float, default=0.0)  # 0 to 100
    severity_reasons_json = Column(Text, default="[]")
    urgent_review_required = Column(Boolean, default=False)

    # Maintenance Prioritization
    priority_level = Column(String(50), default="Routine Monitoring")
    priority_score = Column(Float, default=0.0)
    priority_rationale = Column(Text, default="")
    recommended_action = Column(String(255), default="Continue regular monitoring schedule.")

    # Image Quality Assessment
    brightness_mean = Column(Float, default=0.0)
    contrast_std = Column(Float, default=0.0)
    blur_score = Column(Float, default=0.0)
    is_blurry = Column(Boolean, default=False)
    is_low_light = Column(Boolean, default=False)
    image_width = Column(Integer, default=0)
    image_height = Column(Integer, default=0)

    # Explainable AI (Grad-CAM)
    gradcam_image_path = Column(String(500), nullable=True)

    # Model status transparency
    model_status_json = Column(Text, default="{}")

    inspection = relationship("Inspection", back_populates="results")
