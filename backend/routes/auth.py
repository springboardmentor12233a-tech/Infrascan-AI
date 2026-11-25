"""
Authentication, User Management, and Password Reset API Routes.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db, UserRecord, PasswordResetTokenRecord
from backend.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    UpdateProfileRequest,
    UserResponse,
    TokenResponse,
    MessageResponse
)
from backend.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_reset_token,
    RESET_TOKEN_EXPIRE_HOURS
)

router = APIRouter(prefix="/api/auth", tags=["Authentication & User Management"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> UserRecord:
    """
    FastAPI dependency: extracts and verifies the authenticated user.
    Checks 'Authorization: Bearer <token>' header first, then fallback to 'infrascan_token' cookie.
    """
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    if not token:
        token = request.cookies.get("infrascan_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided. Please log in."
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please log in again."
        )

    user_id = payload["sub"]
    user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
    if not user or user.is_active != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or has been disabled."
        )

    return user


def get_optional_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[UserRecord]:
    """Optional auth dependency: returns User if authenticated, else None."""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new inspector account"
)
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user account with default 'Inspector' role."""
    clean_email = payload.email.lower().strip()
    
    # Check duplicate email
    existing = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{clean_email}' already exists. Please sign in or use Forgot Password."
        )

    h_pwd, salt = hash_password(payload.password)
    new_user = UserRecord(
        id=f"USR-{uuid.uuid4().hex[:8].upper()}",
        email=clean_email,
        hashed_password=h_pwd,
        salt=salt,
        full_name=payload.full_name.strip(),
        role="Inspector",  # Non-admin default role to prevent self-elevation
        is_active=1,
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(**new_user.to_dict())


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT session"
)
def login_user(payload: UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticates email & password, sets secure HTTP-only cookie, and returns access token."""
    clean_email = payload.email.lower().strip()
    user = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()

    if not user or not verify_password(payload.password, user.hashed_password, user.salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials."
        )

    if user.is_active != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact the administrator."
        )

    # If the user explicitly requested Admin role login, verify they are indeed an Admin
    if payload.role and payload.role.strip().lower() == "admin":
        if user.role.lower() != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Account '{clean_email}' has role '{user.role}', not 'Admin'. Please select your assigned role."
            )

    # Generate JWT Token
    access_token = create_access_token(data={
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.full_name
    })

    # Set secure HTTP-only cookie for seamless browser navigation
    response.set_cookie(
        key="infrascan_token",
        value=access_token,
        max_age=86400,
        httponly=True,
        samesite="lax",
        secure=False  # Set to True in production HTTPS
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(**user.to_dict())
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a secure password reset token"
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Initiates password reset. Generates a secure 1-hour token."""
    clean_email = payload.email.lower().strip()
    user = db.query(UserRecord).filter(func.lower(UserRecord.email) == clean_email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered account found with email '{clean_email}'."
        )

    # Expire any previous active tokens for this user
    db.query(PasswordResetTokenRecord).filter(
        PasswordResetTokenRecord.user_id == user.id,
        PasswordResetTokenRecord.is_used == 0
    ).update({"is_used": 1})

    reset_token = generate_reset_token()
    token_record = PasswordResetTokenRecord(
        id=f"RST-{uuid.uuid4().hex[:8].upper()}",
        user_id=user.id,
        token=reset_token,
        expires_at=datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS),
        is_used=0,
        created_at=datetime.utcnow()
    )
    db.add(token_record)
    db.commit()

    reset_link = f"/reset-password?token={reset_token}"
    print(f"[Auth Security] Password reset initiated for {clean_email}.")
    print(f"                Dev Reset Link: {reset_link}")

    return MessageResponse(
        status="success",
        message="A secure password reset link has been generated.",
        detail=(
            "In development mode, the reset link is provided directly below. "
            "For production deployment, configure SMTP environment variables "
            "(SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD) in .env to dispatch emails."
        ),
        dev_reset_link=reset_link
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using valid reset token"
)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Resets password for the token holder and marks token as used."""
    token_record = db.query(PasswordResetTokenRecord).filter(
        PasswordResetTokenRecord.token == payload.token
    ).first()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token."
        )

    if token_record.is_used == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset token has already been used. Please request a new one."
        )

    if datetime.utcnow() > token_record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset token has expired. Tokens are valid for 1 hour."
        )

    user = db.query(UserRecord).filter(UserRecord.id == token_record.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated user account no longer exists."
        )

    h_pwd, salt = hash_password(payload.new_password)
    user.hashed_password = h_pwd
    user.salt = salt
    user.updated_at = datetime.utcnow()
    token_record.is_used = 1

    db.commit()

    return MessageResponse(
        status="success",
        message="Password has been successfully updated. You can now log in with your new credentials."
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile"
)
def get_profile(current_user: UserRecord = Depends(get_current_user)):
    """Returns profile for currently authenticated user."""
    return UserResponse(**current_user.to_dict())


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update profile details"
)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates full name and/or email for the logged-in user."""
    if payload.email:
        clean_email = payload.email.lower().strip()
        if clean_email != current_user.email.lower():
            # Check duplicate email
            existing = db.query(UserRecord).filter(
                func.lower(UserRecord.email) == clean_email,
                UserRecord.id != current_user.id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"An account with email '{clean_email}' already exists. Please choose a different email."
                )
            current_user.email = clean_email

    if payload.full_name:
        current_user.full_name = payload.full_name.strip()

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return UserResponse(**current_user.to_dict())


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password for authenticated user"
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verifies existing password and updates to new password."""
    if not verify_password(payload.current_password, current_user.hashed_password, current_user.salt):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    h_pwd, salt = hash_password(payload.new_password)
    current_user.hashed_password = h_pwd
    current_user.salt = salt
    current_user.updated_at = datetime.utcnow()
    db.commit()

    return MessageResponse(
        status="success",
        message="Password changed successfully."
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out and clear session cookie"
)
def logout_user(response: Response):
    """Clears HTTP-only session cookie."""
    response.delete_cookie(key="infrascan_token", path="/")
    return MessageResponse(status="success", message="Logged out successfully.")
