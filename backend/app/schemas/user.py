from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Schema for user registration (role is not selectable by user)
class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=10, description="Password must be at least 10 characters")


# Schema returned upon successful login / token refresh
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    role: str


# Schema for refreshing token
class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Opaque refresh token")


# Public/Safe user representation
class UserResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Schema for updating profile full name
class UserUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)


# Schema for changing password
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=10, description="New password must be at least 10 characters")


# Forgot and reset password requests
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=10, description="New password must be at least 10 characters")


# Admin creation of user with specific role
class AdminCreateUserRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=10)
    role: str = Field(default="inspector")


# Schema for admin updating a user's role
class UpdateRoleRequest(BaseModel):
    role: str


# Schema for admin updating a user's active status
class UpdateActiveRequest(BaseModel):
    is_active: bool


# Schema for active user sessions
class UserSessionResponse(BaseModel):
    session_id: str
    user_agent: Optional[str] = None
    ip: Optional[str] = None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)


# Schema for audit logs
class AuditLogResponse(BaseModel):
    log_id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedUsersResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


class PaginatedAuditLogsResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
