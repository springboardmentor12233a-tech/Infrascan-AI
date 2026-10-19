from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.inspection import ALLOWED_INSPECTION_STATUSES


# Request schema for creating an inspection
class InspectionCreate(BaseModel):
    asset_id: int
    inspector_id: int
    inspection_date: date
    status: str = "assigned"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ALLOWED_INSPECTION_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(ALLOWED_INSPECTION_STATUSES)}")
        return v


# Request schema for updating inspection status
class InspectionStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ALLOWED_INSPECTION_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(ALLOWED_INSPECTION_STATUSES)}")
        return v


# Full inspection response representation
class InspectionResponse(BaseModel):
    inspection_id: int
    asset_id: int
    asset_name: str | None = None
    inspector_id: int
    inspector_name: str | None = None
    inspection_date: date
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Compact inspection summary for asset details
class InspectionSummaryResponse(BaseModel):
    inspection_id: int
    inspector_id: int
    inspector_name: str | None = None
    inspection_date: date
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
