from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AuthIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class AssetIn(BaseModel):
    asset_id: str = Field(min_length=1, max_length=64)
    name: str
    type: str
    location: str
    construction_year: int | None = None
    material: str | None = None
    department: str | None = None
    inspection_frequency: str | None = None
    maintenance_history: str | None = None


class AssetOut(AssetIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class InspectionIn(BaseModel):
    asset_id: int
    status: str = "scheduled"
    notes: str | None = None


class InspectionOut(InspectionIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
