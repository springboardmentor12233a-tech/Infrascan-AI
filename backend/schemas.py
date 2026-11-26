import sys, os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class AssetBase(BaseModel):
    name: str
    type: str
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    construction_year: Optional[int] = None
    material_type: Optional[str] = "Reinforced Concrete"
    responsible_dept: Optional[str] = "Infrastructure Maintenance"

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class InspectionCreate(BaseModel):
    asset_id: Optional[int] = None
    inspector_name: Optional[str] = "Civil Engineer Inspector"
    notes: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class DetectionBox(BaseModel):
    box: List[int] # [x1, y1, x2, y2]
    confidence: float
    label: str

class InspectionResultResponse(BaseModel):
    id: int
    inspection_id: int
    crack_detected: bool
    crack_probability: float
    surface_type: str
    defect_count: int
    detections: List[Dict[str, Any]]
    
    # Images (relative URLs or paths)
    mask_url: Optional[str] = None
    overlay_url: Optional[str] = None
    gradcam_url: Optional[str] = None
    original_url: Optional[str] = None

    # Geometry & Measurements
    crack_area_px: int
    crack_area_ratio: float
    skeleton_length_px: float
    mean_width_px: float
    max_width_px: float
    crack_density: float
    orientation_angle: float
    num_branches: int
    num_components: int
    is_calibrated: bool
    estimated_length_mm: Optional[float] = None
    estimated_max_width_mm: Optional[float] = None

    # Severity & Maintenance
    severity_level: str
    severity_score: float
    severity_reasons: List[str]
    urgent_review_required: bool
    priority_level: str
    priority_score: float
    priority_rationale: str
    recommended_action: str

    # Quality
    brightness_mean: float
    contrast_std: float
    blur_score: float
    is_blurry: bool
    is_low_light: bool
    image_width: int
    image_height: int

    # Model status
    model_status: Dict[str, Any]

class InspectionResponse(BaseModel):
    id: int
    asset_id: Optional[int] = None
    asset_name: Optional[str] = None
    image_filename: str
    timestamp: datetime
    inspector_name: str
    notes: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_source: str
    result: Optional[InspectionResultResponse] = None

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_inspections: int
    total_assets: int
    cracked_count: int
    severity_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    defect_categories: Dict[str, int]
    recent_inspections: List[Dict[str, Any]]

class HistoricalComparisonResponse(BaseModel):
    asset_id: int
    asset_name: str
    inspections_count: int
    timeline: List[Dict[str, Any]]
    area_progression_px: List[Dict[str, Any]]
    severity_trend: List[str]
    summary_change: str
