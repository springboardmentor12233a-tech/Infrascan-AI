"""InfraScan Pydantic Schemas."""
from .prediction import (
    ClassificationResponse,
    SegmentationResponse,
    CombinedPredictionResponse,
    HealthResponse
)

__all__ = [
    "ClassificationResponse",
    "SegmentationResponse",
    "CombinedPredictionResponse",
    "HealthResponse"
]

