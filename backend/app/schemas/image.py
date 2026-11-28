from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.models.inspection_image import QualityStatus


class ImageOut(BaseModel):
    id: int
    inspection_id: int
    file_path: str
    original_filename: str
    md5_hash: str
    width: int
    height: int
    file_size_kb: float
    blur_score: Optional[float] = None
    brightness: Optional[float] = None
    quality_status: QualityStatus
    has_crack: Optional[bool] = None
    confidence_score: Optional[float] = None
    severity_level: Optional[str] = None
    crack_type: Optional[str] = None
    crack_length_px: Optional[int] = None
    max_crack_width_px: Optional[float] = None
    avg_crack_width_px: Optional[float] = None
    crack_density_pct: Optional[float] = None
    crack_area_px: Optional[int] = None
    crack_length_mm: Optional[float] = None
    max_crack_width_mm: Optional[float] = None
    avg_crack_width_mm: Optional[float] = None
    crack_area_mm2: Optional[float] = None
    orientation_deg: Optional[float] = None
    branching_points: Optional[int] = None
    calibration_mm_per_px: Optional[float] = 0.2
    bounding_boxes: Optional[str] = None
    damage_types: Optional[str] = None
    risk_score: Optional[float] = None
    uploaded_at: datetime
    url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
