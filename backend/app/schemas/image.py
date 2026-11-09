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
    bounding_boxes: Optional[str] = None
    uploaded_at: datetime
    url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
