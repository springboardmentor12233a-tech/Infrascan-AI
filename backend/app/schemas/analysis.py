from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ImageAnalysisOut(BaseModel):
    id: int
    image_id: int
    inspection_id: int
    quality: dict[str, Any]
    classification_status: str
    classification_label: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification: dict[str, Any]
    detection_status: str
    detection: dict[str, Any]
    segmentation_status: str
    segmentation: dict[str, Any]
    geometry: dict[str, Any]
    overlay_url: Optional[str] = None
    mask_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelStatusOut(BaseModel):
    classifier: dict[str, Any]
    segmentation: dict[str, Any]
    detection: dict[str, Any]


class DashboardStats(BaseModel):
    assets: int
    inspections: int
    images: int
    analyses: int
