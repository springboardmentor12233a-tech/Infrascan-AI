from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from app.models.infrastructure_asset import AssetType
from app.models.inspection import InspectionStatus
from app.schemas.user import UserOut


# --- Asset Schemas ---
class AssetBase(BaseModel):
    asset_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    type: AssetType
    location_text: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude between -180 and 180")
    construction_year: Optional[int] = Field(None, ge=1800, le=2100, description="Construction year (1800-2100)")
    material_type: Optional[str] = Field(None, max_length=100)
    responsible_department: Optional[str] = Field(None, max_length=200)
    inspection_frequency_days: Optional[int] = Field(None, ge=1)
    maintenance_history: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    asset_code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    type: Optional[AssetType] = None
    location_text: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    construction_year: Optional[int] = Field(None, ge=1800, le=2100)
    material_type: Optional[str] = None
    responsible_department: Optional[str] = None
    inspection_frequency_days: Optional[int] = Field(None, ge=1)
    maintenance_history: Optional[str] = None


class AssetOut(AssetBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[AssetOut]


# --- Inspection Schemas ---
class InspectionBase(BaseModel):
    asset_id: int
    inspector_id: int
    inspection_date: date
    notes: Optional[str] = None


class InspectionCreate(InspectionBase):
    status: Optional[InspectionStatus] = InspectionStatus.PENDING


class InspectionUpdate(BaseModel):
    inspector_id: Optional[int] = None
    inspection_date: Optional[date] = None
    status: Optional[InspectionStatus] = None
    notes: Optional[str] = None


class InspectionOut(InspectionBase):
    id: int
    status: InspectionStatus
    created_at: datetime
    inspector: Optional[UserOut] = None
    asset: Optional[AssetOut] = None

    model_config = ConfigDict(from_attributes=True)
