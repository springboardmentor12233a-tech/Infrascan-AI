"""Pydantic schemas for damage severity assessment."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FactorDetail(BaseModel):
    factor: str
    input_value: Any
    points: float
    note: Optional[str] = None


class SeverityAssessmentResponse(BaseModel):
    assessment_id: int
    run_id: int
    image_id: int
    severity_level: str
    score: float
    priority_suggestion: str
    factors_json: str
    warnings_json: Optional[str] = None
    rules_version: str
    rules_sha256: str
    review_status: str
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    final_severity: Optional[str] = None
    final_priority: Optional[str] = None
    review_comment: Optional[str] = None
    is_superseded: bool = False
    created_at: datetime
    factors: Optional[List[FactorDetail]] = None
    warnings: Optional[List[str]] = None
    needs_review: bool = True
    low_confidence_review: bool = False

    model_config = ConfigDict(from_attributes=True)


class ReviewActionRequest(BaseModel):
    action: str = Field(..., description="Action: 'confirm' or 'correct'")
    final_severity: Optional[str] = Field(None, description="Required when action is 'correct'")
    final_priority: Optional[str] = Field(None, description="Optional override for priority")
    comment: Optional[str] = Field(None, description="Required when action is 'correct'")


class InspectionSeverityResponse(BaseModel):
    id: int
    inspection_id: int
    worst_severity: str
    worst_score: float
    images_assessed: int
    images_pending_review: int
    summary_json: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InspectionSeverityDetailResponse(BaseModel):
    inspection_id: int
    worst_severity: str
    worst_score: float
    images_assessed: int
    images_pending_review: int
    summary: Optional[Dict[str, Any]] = None
    assessments: List[SeverityAssessmentResponse] = []


class SeverityRulesResponse(BaseModel):
    rules_version: str
    status: str
    rules_sha256: str
    rules: Dict[str, Any]

