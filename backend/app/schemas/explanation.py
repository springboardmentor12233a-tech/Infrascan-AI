"""Pydantic schemas for Explainable AI (XAI) requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExplainRequest(BaseModel):
    """Optional payload to trigger explanation generation for specific models and methods."""
    models: Optional[List[str]] = Field(
        None,
        description="List of model IDs to explain (e.g. ['unetplusplus_crack500', 'yolov8s_rdd2022', 'A2_rtdetr_l']). Defaults to all models in the latest run."
    )
    methods: Optional[List[str]] = Field(
        None,
        description="List of explanation methods (e.g. ['gradcam', 'gradcampp', 'eigencam', 'saliency']). Defaults to standard methods per model."
    )


class ExplanationResponse(BaseModel):
    """Response representing a single model explanation."""
    explanation_id: int
    run_id: int
    image_id: int
    model_id: str
    method: str
    target: str
    heatmap_path: Optional[str] = None
    overlay_path: Optional[str] = None
    overlay_url: Optional[str] = None
    heatmap_url: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    seconds: Optional[float] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompareMapsRequest(BaseModel):
    """Request to compute similarity metrics between two generated attention maps."""
    explanation_id_a: int
    explanation_id_b: int


class CompareMapsResponse(BaseModel):
    """Response containing map similarity and correlation metrics."""
    explanation_id_a: int
    explanation_id_b: int
    spearman_correlation: float
    top_10_overlap: float
    interpretation: str
