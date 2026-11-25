import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.session import LoginAttempt, PasswordResetToken, UserSession
from app.models.user import User
from app.services.audit import create_audit_log
from app.services.security import generate_opaque_token, hash_token


def is_account_locked(db: Session, email: Optional[str], ip: Optional[str]) -> bool:
    """Check if the email or IP has exceeded failed login threshold within the lockout window."""
    window_minutes = getattr(settings, "LOCKOUT_WINDOW_MINUTES", 15)
    max_attempts = getattr(settings, "LOCKOUT_ATTEMPTS", 5)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    query = db.query(LoginAttempt).filter(
        LoginAttempt.attempt_at >= cutoff if hasattr(LoginAttempt, "attempt_at") else LoginAttempt.created_at >= cutoff,
        LoginAttempt.success == False,
    )
    if email:
        email_failures = query.filter(LoginAttempt.email == email).count()
        if email_failures >= max_attempts:
            return True
    if ip:
        ip_failures = query.filter(LoginAttempt.ip_address == ip).count()
        if ip_failures >= max_attempts:
            return True
    return False


def record_login_attempt(db: Session, email: Optional[str], ip: Optional[str], success: bool) -> None:
    """Record a login attempt in the database."""
    attempt = LoginAttempt(email=email, ip_address=ip, success=success)
    db.add(attempt)
    db.commit()


def create_user_session(
    db: Session,
    user_id: int,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
    family_id: Optional[str] = None,
) -> Tuple[UserSession, str]:
    """Create a new session record with an opaque refresh token."""
    raw_token = generate_opaque_token(32)
    token_h = hash_token(raw_token)
    session_id = str(uuid.uuid4())
    fam_id = family_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expire_days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)
    expires_at = now + timedelta(days=expire_days)

    session = UserSession(
        session_id=session_id,
        user_id=user_id,
        token_hash=token_h,
        family_id=fam_id,
        user_agent=user_agent[:500] if user_agent else None,
        ip=ip[:100] if ip else None,
        created_at=now,
        last_used_at=now,
        expires_at=expires_at,
        revoked_at=None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, raw_token


def rotate_refresh_token(
    db: Session,
    raw_refresh_token: str,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> Tuple[UserSession, str, User]:
    """Rotate a refresh token, detecting reuse and revoking families when violated."""
    token_h = hash_token(raw_refresh_token)
    session = db.query(UserSession).filter(UserSession.token_hash == token_h).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check for reuse
    if session.revoked_at is not None:
        # Revoke the entire family
        db.query(UserSession).filter(UserSession.family_id == session.family_id).update(
            {"revoked_at": datetime.now(timezone.utc)}
        )
        db.commit()
        create_audit_log(
            db=db,
            action="refresh_token_reuse_detected",
            user_id=session.user_id,
            entity_type="session",
            entity_id=session.session_id,
            ip_address=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Revoked refresh token reuse detected. All sessions in this family have been terminated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)
    # Check expiration
    if session.expires_at.tzinfo is None:
        session_exp = session.expires_at.replace(tzinfo=timezone.utc)
    else:
        session_exp = session.expires_at
    if session_exp < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check user status
    user = db.query(User).filter(User.user_id == session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive or user not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Revoke old session and issue new token in same family
    session.revoked_at = now
    new_session, new_raw_token = create_user_session(
        db=db,
        user_id=user.user_id,
        user_agent=user_agent,
        ip=ip,
        family_id=session.family_id,
    )
    return new_session, new_raw_token, user


def revoke_user_sessions(
    db: Session,
    user_id: int,
    except_session_id: Optional[str] = None,
) -> int:
    """Revoke active sessions for a user, optionally keeping a specific session."""
    now = datetime.now(timezone.utc)
    query = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.revoked_at.is_(None),
    )
    if except_session_id:
        query = query.filter(UserSession.session_id != except_session_id)
    count = query.update({"revoked_at": now}, synchronize_session=False)
    db.commit()
    return count


def list_user_sessions(db: Session, user_id: int) -> List[UserSession]:
    """Return active unrevoked sessions for a user."""
    now = datetime.now(timezone.utc)
    return (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .order_by(UserSession.last_used_at.desc())
        .all()
    )


def create_password_reset_token(db: Session, user_id: int) -> str:
    """Generate and store single-use password reset token valid for 1 hour."""
    raw_token = generate_opaque_token(32)
    token_h = hash_token(raw_token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)

    record = PasswordResetToken(
        user_id=user_id,
        token_hash=token_h,
        expires_at=expires_at,
        used_at=None,
        created_at=now,
    )
    db.add(record)
    db.commit()
    return raw_token


def verify_and_consume_reset_token(db: Session, raw_token: str) -> User:
    """Verify single-use reset token, mark it used and return the associated user."""
    token_h = hash_token(raw_token)
    record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_h)
        .first()
    )
    if not record or record.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used password reset token",
        )

    now = datetime.now(timezone.utc)
    rec_exp = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
    if rec_exp < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired",
        )

    user = db.query(User).filter(User.user_id == record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive or not found",
        )

    record.used_at = now
    db.commit()
    return user
