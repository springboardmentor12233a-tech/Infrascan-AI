from datetime import date, datetime
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.asset import (
    ALLOWED_ASSET_TYPES,
    ALLOWED_IMPORTANCE_LEVELS,
    ALLOWED_MATERIAL_TYPES,
)
from app.schemas.inspection import InspectionSummaryResponse


# Base schema for infrastructure assets with strict field validations
class AssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Asset name is required")
    asset_type: str = Field(..., description="Type of infrastructure asset")
    material_type: str = Field(..., description="Primary construction material")
    address: str | None = Field(None, max_length=255, description="Physical address or landmark")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude between -90 and 90")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude between -180 and 180")
    construction_year: int = Field(..., description="Year of construction")
    responsible_department: str = Field(..., min_length=1, max_length=100, description="Responsible department")
    inspection_frequency_days: int = Field(..., ge=1, le=3650, description="Inspection frequency in days")
    importance_level: str = Field(..., description="low, medium, or high")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("name is required and cannot be empty")
        return cleaned

    @field_validator("asset_type")
    @classmethod
    def validate_asset_type(cls, v: str) -> str:
        if v not in ALLOWED_ASSET_TYPES:
            raise ValueError(f"asset_type must be one of: {', '.join(ALLOWED_ASSET_TYPES)}")
        return v

    @field_validator("material_type")
    @classmethod
    def validate_material_type(cls, v: str) -> str:
        if v not in ALLOWED_MATERIAL_TYPES:
            raise ValueError(f"material_type must be one of: {', '.join(ALLOWED_MATERIAL_TYPES)}")
        return v

    @field_validator("importance_level")
    @classmethod
    def validate_importance_level(cls, v: str) -> str:
        if v not in ALLOWED_IMPORTANCE_LEVELS:
            raise ValueError(f"importance_level must be one of: {', '.join(ALLOWED_IMPORTANCE_LEVELS)}")
        return v

    @field_validator("construction_year")
    @classmethod
    def validate_construction_year(cls, v: int) -> int:
        current_year = datetime.now().year
        if v < 1800 or v > current_year:
            raise ValueError(f"construction_year must be between 1800 and {current_year}")
        return v


# Request schema for creating an asset
class AssetCreate(AssetBase):
    pass


# Request schema for updating an asset
class AssetUpdate(AssetBase):
    pass


# Standard response representation for an asset
class AssetResponse(AssetBase):
    asset_id: int
    created_by: int | None = None
    created_at: datetime
    last_inspection_date: date | None = None

    model_config = ConfigDict(from_attributes=True)


# Paginated assets list response
class AssetListResponse(BaseModel):
    items: List[AssetResponse]
    total: int
    page: int
    page_size: int


# Detailed asset response including its inspection history
class AssetDetailResponse(AssetResponse):
    inspections: List[InspectionSummaryResponse] = []


# GeoJSON schemas for map integration
class GeoJSONGeometry(BaseModel):
    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude] order per GeoJSON standard


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: Dict[str, Any]  # id, name, type, etc.


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
