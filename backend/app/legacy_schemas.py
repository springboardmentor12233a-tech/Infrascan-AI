from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------- AUTHENTICATION ----------------

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


# ---------------- INFRASTRUCTURE ASSETS ----------------

class AssetIn(BaseModel):
    name: str = Field(..., max_length=150)
    asset_id: str | int | None = None
    type: str | None = None
    asset_type: str = "bridge"
    material: str | None = None
    material_type: str = "concrete"
    location: str | None = None
    address: str | None = None
    latitude: float = 0.0
    longitude: float = 0.0
    construction_year: int = 2020
    department: str | None = None
    responsible_department: str = "Highways"
    inspection_frequency: str | None = None
    inspection_frequency_days: int = 90
    importance_level: str = "medium"
    maintenance_history: str | None = None

    def sync_to_dict(self) -> dict:
        data = self.model_dump()
        if self.type and (not self.asset_type or self.asset_type == "bridge"):
            data["asset_type"] = self.type.lower()
        if self.material and (not self.material_type or self.material_type == "concrete"):
            data["material_type"] = self.material.lower()
        if self.location and not self.address:
            data["address"] = self.location
        if self.department and (not self.responsible_department or self.responsible_department == "Highways"):
            data["responsible_department"] = self.department
        # Clean out non-model fields before passing to InfrastructureAsset
        model_keys = {
            "name", "asset_type", "material_type", "address",
            "latitude", "longitude", "construction_year",
            "responsible_department", "inspection_frequency_days",
            "importance_level", "custom_id"
        }
        if self.asset_id:
            data["custom_id"] = str(self.asset_id)
        return {k: v for k, v in data.items() if k in model_keys}


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    name: str
    asset_id: str | int | None = None
    id: int | None = None
    asset_type: str | None = None
    material_type: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    construction_year: int | None = None
    responsible_department: str | None = None
    inspection_frequency_days: int | None = None
    importance_level: str | None = None
    created_by: int | None = None
    created_at: datetime | None = None


# ---------------- INSPECTIONS ----------------

class InspectionIn(BaseModel):
    asset_id: int
    inspector_id: int
    inspection_date: date
    status: str = "assigned"


class InspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inspection_id: int
    asset_id: int
    inspector_id: int
    inspection_date: date
    status: str
    created_at: datetime

    asset_name: str | None = None
    inspector_name: str | None = None