"""
Pydantic Schemas for InfraScan API Prediction & Dashboard Responses.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field("healthy", description="API health status")
    classification_model_loaded: bool = Field(..., description="Whether classification model is active")
    segmentation_model_loaded: bool = Field(..., description="Whether segmentation model is active")


class ClassificationResponse(BaseModel):
    """Crack classification prediction schema."""
    label: str = Field(..., description="Predicted label: 'Cracked' or 'Uncracked'")
    confidence: float = Field(..., description="Confidence score [0.0 - 1.0] for the predicted label")
    crack_probability: float = Field(..., description="Raw model probability of crack presence [0.0 - 1.0]")
    status: str = Field("success", description="Processing status")
    message: str = Field(..., description="Human-readable assessment message")


class SegmentationResponse(BaseModel):
    """Crack segmentation prediction schema."""
    label: str = Field(..., description="Assessment: 'Crack Detected' or 'No Crack Detected'")
    crack_pixel_count: int = Field(..., description="Total number of crack pixels detected")
    crack_percentage: float = Field(..., description="Percentage of concrete surface area covered by cracks")
    mask_path: str = Field(..., description="Relative filepath of the saved binary mask image")
    overlay_path: str = Field(..., description="Relative filepath of the saved overlay visualization")
    mask_url: Optional[str] = Field(None, description="Direct URL to access the binary mask")
    overlay_url: Optional[str] = Field(None, description="Direct URL to access the visual crack overlay")
    status: str = Field("success", description="Processing status")
    message: str = Field(..., description="Human-readable assessment message")


class CombinedPredictionResponse(BaseModel):
    """Combined classification, segmentation, and damage assessment schema."""
    id: Optional[str] = Field(None, description="Unique inspection identifier")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of analysis")
    classification_label: str = Field(..., description="Classification result: 'Cracked' or 'Uncracked'")
    confidence: float = Field(..., description="Confidence score [0.0 - 1.0] of classification")
    crack_probability: float = Field(..., description="Raw probability score [0.0 - 1.0]")
    segmentation_label: str = Field(..., description="Segmentation result: 'Crack Detected' or 'No Crack Detected'")
    crack_pixel_count: int = Field(..., description="Number of detected crack pixels")
    total_pixels: int = Field(..., description="Total spatial pixels")
    crack_percentage: float = Field(..., description="Crack area coverage percentage")
    severity_level: str = Field("None", description="Preliminary severity: 'None', 'Low', 'Moderate', 'High'")
    damage_assessment: Optional[Dict] = Field(None, description="Detailed civil damage categorization")
    image_path: Optional[str] = Field(None, description="Relative path of saved uploaded image")
    mask_path: str = Field(..., description="Relative filepath of the saved binary mask")
    overlay_path: str = Field(..., description="Relative filepath of the saved overlay")
    image_url: Optional[str] = Field(None, description="Direct URL to view uploaded image")
    mask_url: Optional[str] = Field(None, description="Direct URL to view the binary mask")
    overlay_url: Optional[str] = Field(None, description="Direct URL to view the visual crack overlay")
    report_url: Optional[str] = Field(None, description="Direct URL to download PDF report")
    status: str = Field("success", description="Processing status")
    summary: str = Field(..., description="Consolidated technical damage summary")


class InspectionItemResponse(BaseModel):
    """Schema for individual inspection history record."""
    id: str
    timestamp: Optional[str]
    filename: str
    classification_label: str
    confidence: float
    crack_percentage: float
    severity_level: str
    image_path: str
    overlay_path: str
    mask_path: str
    summary: str


class DashboardStatsResponse(BaseModel):
    """Schema for high-level aggregate dashboard KPIs."""
    total_inspections: int
    cracked_count: int
    uncracked_count: int
    crack_detection_rate: float
    severity_distribution: Dict[str, int]
    recent_inspections: List[Dict]
    models_ready: bool
