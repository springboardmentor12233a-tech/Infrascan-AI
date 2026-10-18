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
    uploaded_at: datetime
    url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
