"""Pydantic schemas for AI analysis runs, detections, crack measurements, and model versions."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DetectionResponse(BaseModel):
    detection_id: int
    run_id: int
    model_id: Optional[str] = None
    damage_type: str
    damage_label: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    model_config = ConfigDict(from_attributes=True)


class CrackMeasurementResponse(BaseModel):
    measurement_id: int
    run_id: int
    mask_path: str
    threshold: float
    crack_pixels: int
    length_px: float
    avg_width_px: float
    max_width_px: float
    p95_width_px: float
    area_px: int
    density_percent: float
    orientation_deg: float
    num_components: int
    num_branch_points: int
    num_end_points: int
    mm_per_pixel: Optional[float] = None
    length_mm: Optional[float] = None
    avg_width_mm: Optional[float] = None
    max_width_mm: Optional[float] = None
    width_mode: str = "edt2"
    scale_id: Optional[int] = None
    length_mm_uncertainty: Optional[float] = None
    width_mm_uncertainty: Optional[float] = None
    measurement_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ModelVersionResponse(BaseModel):
    model_id: str
    model_name: str
    task: str
    version: str
    weights_path: str
    threshold: float
    class_names_json: Optional[str] = None
    metrics_json: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisRunResponse(BaseModel):
    run_id: int
    image_id: int
    status: str
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    seconds: Optional[float] = None
    image_scale_note: Optional[str] = None
    detections: List[DetectionResponse] = []
    crack_measurements: List[CrackMeasurementResponse] = []
    model_ids: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class AnalyzeImageRequest(BaseModel):
    mm_per_pixel: Optional[float] = Field(
        default=None,
        description="Physical scale in millimeters per pixel for converting pixel measurements to metric units."
    )
    detectors: Optional[List[str]] = Field(
        default=None,
        description="Optional list of detector names to override default asset-type selection (allowed for admin and civil_engineer only)."
    )


class DetectorInfoResponse(BaseModel):
    name: str
    classes: List[str]
    conf: float
    imgsz: int
    applicable_asset_types: List[str]
    domain_note: str
    validation_metrics: Optional[Dict[str, Any]] = None


class AnalyzeBatchResponse(BaseModel):
    enqueued_count: int
    run_ids: List[int]
    message: str


class SetScaleRequest(BaseModel):
    method: Optional[str] = None  # "manual_ratio" or "reference_object"
    mm_per_pixel: Optional[float] = None
    reference_mm: Optional[float] = None
    point1_x: Optional[float] = None
    point1_y: Optional[float] = None
    point2_x: Optional[float] = None
    point2_y: Optional[float] = None
    point1: Optional[List[float]] = None
    point2: Optional[List[float]] = None
    camera_perpendicular: bool = True


class ImageScaleResponse(BaseModel):
    scale_id: int
    image_id: int
    method: str
    mm_per_pixel: float
    reference_mm: Optional[float] = None
    reference_px: Optional[float] = None
    point1_x: Optional[float] = None
    point1_y: Optional[float] = None
    point2_x: Optional[float] = None
    point2_y: Optional[float] = None
    camera_perpendicular: bool
    uncertainty_percent: float
    is_current: bool
    set_by: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

