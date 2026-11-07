from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


# Schema for user registration (role is not selectable by user)
class UserRegisterRequest(BaseModel):
    full_name: str | None = None
    name: str | None = None
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")

    @model_validator(mode="after")
    def populate_name(self):
        if not self.full_name:
            self.full_name = self.name or self.email.split("@")[0]
        return self


# Schema returned upon successful login
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int | None = None
    email: str | None = None
    full_name: str | None = None


# Public/Safe user representation
class UserResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    access_token: str | None = None
    token_type: str | None = "bearer"

    model_config = ConfigDict(from_attributes=True)


# Schema for updating profile full name
class UserUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)


# Schema for changing password
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, description="New password must be at least 8 characters")


# Schema for admin updating a user's role
class UpdateRoleRequest(BaseModel):
    role: str


# Schema for admin updating a user's active status
class UpdateActiveRequest(BaseModel):
    is_active: bool
