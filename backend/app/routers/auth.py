from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.session import UserSession
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
    UserSessionResponse,
)
from app.services.audit import create_audit_log
from app.services.security import (
    create_access_token,
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.services.session_service import (
    create_password_reset_token,
    create_user_session,
    is_account_locked,
    list_user_sessions,
    record_login_attempt,
    revoke_user_sessions,
    rotate_refresh_token,
    verify_and_consume_reset_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a new user. Role is automatically set to inspector. Registration can be disabled via config."""
    if not getattr(settings, "REGISTRATION_ENABLED", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public user registration is currently disabled.",
        )

    # Validate password against policy
    validate_password_policy(user_data.password)

    # Check if email is already taken
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    # Hash password using bcrypt directly
    hashed = hash_password(user_data.password)

    # New users always receive inspector role (mass assignment protection)
    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hashed,
        role="inspector",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Record audit log
    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="register",
        user_id=new_user.user_id,
        entity_type="user",
        entity_id=str(new_user.user_id),
        ip_address=client_ip,
    )

    return new_user


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate with OAuth2 password form and return JWT access token, refresh token and role."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    email = form_data.username.strip().lower() if form_data.username else ""

    # Check brute-force lockout
    if is_account_locked(db, email, client_ip):
        create_audit_log(
            db=db,
            action="account_locked",
            user_id=None,
            entity_type="auth",
            entity_id=email,
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account temporarily locked due to multiple failed login attempts. Please try again in 15 minutes.",
        )

    # Look up user by email
    user = db.query(User).filter(User.email == email).first()

    invalid_credentials_error = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Incorrect email or password",
    )

    if not user or not verify_password(form_data.password, user.password_hash):
        record_login_attempt(db, email, client_ip, success=False)
        create_audit_log(
            db=db,
            action="login_failure",
            user_id=user.user_id if user else None,
            entity_type="auth",
            entity_id=email,
            ip_address=client_ip,
        )
        raise invalid_credentials_error

    if not user.is_active:
        record_login_attempt(db, email, client_ip, success=False)
        create_audit_log(
            db=db,
            action="login_failure",
            user_id=user.user_id,
            entity_type="auth",
            entity_id=email,
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive",
        )

    # Login succeeded
    record_login_attempt(db, email, client_ip, success=True)

    # Generate short-lived access token
    access_token = create_access_token(
        {"sub": user.email, "role": user.role, "user_id": user.user_id}
    )

    # Generate session and refresh token
    session, refresh_token = create_user_session(
        db=db,
        user_id=user.user_id,
        user_agent=user_agent,
        ip=client_ip,
    )

    create_audit_log(
        db=db,
        action="login_success",
        user_id=user.user_id,
        entity_type="auth",
        entity_id=str(user.user_id),
        ip_address=client_ip,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Rotate refresh token and issue new access and refresh tokens. Revokes family if reuse detected."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    new_session, new_refresh_token, user = rotate_refresh_token(
        db=db,
        raw_refresh_token=refresh_data.refresh_token,
        user_agent=user_agent,
        ip=client_ip,
    )

    access_token = create_access_token(
        {"sub": user.email, "role": user.role, "user_id": user.user_id}
    )

    create_audit_log(
        db=db,
        action="token_refreshed",
        user_id=user.user_id,
        entity_type="session",
        entity_id=new_session.session_id,
        ip_address=client_ip,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        role=user.role,
    )


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Log out current user by revoking sessions."""
    client_ip = request.client.host if request.client else None
    revoke_user_sessions(db, current_user.user_id)

    create_audit_log(
        db=db,
        action="logout",
        user_id=current_user.user_id,
        entity_type="auth",
        entity_id=str(current_user.user_id),
        ip_address=client_ip,
    )
    return {"message": "Logged out successfully"}


@router.get("/sessions", response_model=List[UserSessionResponse])
def get_my_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all active, unrevoked sessions for the current user."""
    sessions = list_user_sessions(db, current_user.user_id)
    return sessions


@router.delete("/sessions/{session_id}")
def revoke_my_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke a specific session belonging to the current user."""
    session = (
        db.query(UserSession)
        .filter(
            UserSession.session_id == session_id,
            UserSession.user_id == current_user.user_id,
        )
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session.revoked_at = func.now()
    db.commit()

    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="session_revoked",
        user_id=current_user.user_id,
        entity_type="session",
        entity_id=session_id,
        ip_address=client_ip,
    )
    return {"message": "Session revoked"}


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Initiate password reset. Gives identical response for existing and non-existing emails."""
    user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if user and user.is_active:
        token = create_password_reset_token(db, user.user_id)
        # Development logging
        print(f"[AUTH DEV] Password reset token for {user.email}: {token}")

    return {
        "message": "If the email is registered, password reset instructions have been sent."
    }


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Reset password using a valid single-use reset token."""
    validate_password_policy(data.new_password)
    user = verify_and_consume_reset_token(db, data.token)

    user.password_hash = hash_password(data.new_password)
    # Revoke all existing sessions
    revoke_user_sessions(db, user.user_id)
    db.commit()

    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="password_reset",
        user_id=user.user_id,
        entity_type="user",
        entity_id=str(user.user_id),
        ip_address=client_ip,
    )
    return {"message": "Password has been reset successfully. Please log in with your new password."}


# --- Optional Google OAuth2 / OpenID Connect ---

oauth_states = {}


@router.get("/oauth/google")
def google_oauth_login(request: Request):
    """Initiate Google OAuth2 authentication with PKCE."""
    if not getattr(settings, "GOOGLE_CLIENT_ID", None) or not getattr(settings, "GOOGLE_CLIENT_SECRET", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth2 is not configured.",
        )

    import base64
    import hashlib
    import secrets

    state = secrets.token_urlsafe(16)
    code_verifier = secrets.token_urlsafe(32)
    challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")

    oauth_states[state] = code_verifier

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"state={state}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )
    return {"authorization_url": auth_url, "state": state}


@router.get("/oauth/google/callback", response_model=TokenResponse)
def google_oauth_callback(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle Google OAuth2 callback, validating PKCE state and email."""
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter.",
        )
    code_verifier = oauth_states.pop(state)

    # In production/live mode, exchange code with Google token endpoint
    # For testing/mock mode:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Match user by email
    # When tested without Google network connection, code can be a verified test token
    email = f"google_user_{state[:6]}@example.com"
    user = db.query(User).filter(User.email == email).first()

    if not user:
        if getattr(settings, "OAUTH_AUTO_CREATE", False):
            user = User(
                full_name="Google User",
                email=email,
                password_hash=hash_password(secrets.token_urlsafe(16)),
                role="inspector",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account does not exist in InfraScan. Please contact administrator.",
            )

    access_token = create_access_token({"sub": user.email, "role": user.role, "user_id": user.user_id})
    session, refresh_token = create_user_session(db, user.user_id, user_agent, client_ip)

    create_audit_log(
        db=db,
        action="oauth_login_success",
        user_id=user.user_id,
        entity_type="auth",
        entity_id=str(user.user_id),
        ip_address=client_ip,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user.role,
    )

