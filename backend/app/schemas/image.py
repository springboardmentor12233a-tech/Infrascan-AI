from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


# Schema for full image metadata
class ImageResponse(BaseModel):
    image_id: int
    inspection_id: int
    uploaded_by: Optional[int] = None
    file_path: str
    original_filename: str
    file_hash: str
    width_px: int
    height_px: int
    file_size_bytes: int
    source: str
    blur_score: float
    brightness_score: float
    quality_status: str
    quality_notes: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    captured_at: Optional[datetime] = None
    uploaded_at: datetime
    processed_file_path: Optional[str] = None
    preprocess_status: str = "not_run"
    preprocess_steps: Optional[str] = None
    preprocessed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Result for a single uploaded file in a batch
class UploadResultItem(BaseModel):
    filename: str
    status: str  # "accepted", "warning", "rejected"
    message: str
    image: Optional[ImageResponse] = None


# Overall response for a batch upload
class UploadBatchResponse(BaseModel):
    total_files: int
    accepted_count: int
    warning_count: int
    rejected_count: int
    results: List[UploadResultItem]
