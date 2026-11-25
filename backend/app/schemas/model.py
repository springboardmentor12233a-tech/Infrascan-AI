from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_id: str
    model_name: str
    task: str
    version: str
    weights_path: str
    threshold: float
    class_names: Optional[Dict[str, str]] = None
    metrics: Optional[Dict[str, Any]] = None
    is_active: bool
    inferences_count: int
    mean_inference_time_ms: float
    last_inference_at: Optional[datetime] = None
    error_count: int
    created_at: datetime


class ModelEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: str
    event_type: str
    performed_by: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    created_at: datetime


class DatasetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    version: str
    task: str
    split_stats: Optional[Dict[str, Any]] = None
    created_at: datetime


class ClassifyCropResponse(BaseModel):
    crack_probability: float
    is_cracked: bool
    label: str
    threshold: float
    model_id: str
    crop_dimensions: Dict[str, int]
    latency_ms: float
    screening_disclaimer: str
