from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional


# --- Roles ---
class RoleOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Password at least 6 characters")
    role_id: Optional[int] = Field(default=None, description="Optional role ID. Default assigned if None.")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class UserOut(UserBase):
    id: int
    role_id: int
    role: Optional[RoleOut] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdate(BaseModel):
    role_id: int
    is_active: Optional[bool] = None


# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None
