"""
Authentication Pydantic Request & Response Schemas.
"""

import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Payload for user registration."""
    email: EmailStr = Field(..., description="Valid work/inspector email address")
    full_name: str = Field(..., min_length=2, max_length=150, description="Full name of inspector")
    password: str = Field(..., min_length=8, max_length=128, description="Password (at least 8 characters)")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Matching confirm password")

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match.")
        return v

    @field_validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v


class UserLoginRequest(BaseModel):
    """Payload for user login."""
    email: EmailStr = Field(..., description="Registered user email")
    password: str = Field(..., description="Account password")
    role: Optional[str] = Field("Admin", description="Requested role login (initially Admin)")


class ForgotPasswordRequest(BaseModel):
    """Payload to initiate password reset."""
    email: EmailStr = Field(..., description="Registered email to receive password reset link")


class ResetPasswordRequest(BaseModel):
    """Payload to complete password reset using secure token."""
    token: str = Field(..., min_length=16, description="Cryptographic reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New account password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match.")
        return v


class ChangePasswordRequest(BaseModel):
    """Payload for an authenticated user changing their password."""
    current_password: str = Field(..., description="Current active password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match.")
        return v


class UpdateProfileRequest(BaseModel):
    """Payload for updating user profile information."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[EmailStr] = Field(None, description="Updated work/inspector email address")


class UserResponse(BaseModel):
    """User profile data returned to client."""
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TokenResponse(BaseModel):
    """Access token and user profile returned on successful login."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Standard operation message response."""
    status: str = "success"
    message: str
    detail: Optional[str] = None
    dev_reset_link: Optional[str] = None
