from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = "Viewer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class AssetCreate(BaseModel):
    asset_code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    infrastructure_type: str
    description: str | None = None
    location_name: str
    latitude: float | None = None
    longitude: float | None = None
    construction_year: int | None = None
    material_type: str | None = None
    owner: str | None = None


class AssetUpdate(BaseModel):
    name: str | None = None
    infrastructure_type: str | None = None
    description: str | None = None
    location_name: str | None = None
    asset_status: str | None = None


class AssetOut(BaseModel):
    id: str
    asset_code: str
    name: str
    infrastructure_type: str
    location_name: str
    latitude: float | None
    longitude: float | None
    construction_year: int | None
    material_type: str | None
    asset_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InspectionCreate(BaseModel):
    inspection_code: str
    asset_id: str
    inspection_type: str = "Routine Inspection"
    inspection_date: str
    inspector_id: str | None = None
    weather_conditions: str | None = None
    inspection_notes: str | None = None


class InspectionOut(BaseModel):
    id: str
    inspection_code: str
    asset_id: str
    inspection_type: str
    inspection_date: str
    inspector_id: str | None
    inspection_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisCreate(BaseModel):
    asset_id: str
    inspection_id: str
    image_id: str
    pipeline_type: str = "Complete Damage Analysis"
    selected_models: list[str] = ["YOLO-Crack", "U-Net-Seg"]


class AnalysisOut(BaseModel):
    id: str
    analysis_code: str
    asset_id: str
    inspection_id: str
    image_id: str
    pipeline_type: str
    job_status: str
    progress_percentage: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    review_decision: str
    corrected_category: str | None = None
    corrected_severity: str | None = None
    engineering_notes: str | None = None

