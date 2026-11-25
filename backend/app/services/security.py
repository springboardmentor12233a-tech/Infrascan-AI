import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
import jwt
from fastapi import HTTPException, status
from app.config import settings

ALGORITHM = "HS256"

COMMON_PASSWORDS_BLOCKLIST = {
    "password1234",
    "1234567890",
    "qwerty1234",
    "admin12345",
    "welcome1234",
    "infrascan1234",
    "letmein1234",
    "changeme1234",
}


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt directly."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def validate_password_policy(password: str) -> None:
    """Validate password against length and blocklist rules."""
    min_len = getattr(settings, "PASSWORD_MIN_LENGTH", 10)
    if len(password) < min_len:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {min_len} characters long.",
        )
    if password.lower() in COMMON_PASSWORDS_BLOCKLIST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too common and insecure. Please choose a stronger password.",
        )


def generate_opaque_token(nbytes: int = 32) -> str:
    """Generate cryptographically secure opaque URL-safe token."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Compute SHA256 hex digest for opaque token storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token with standard claims."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    expire = now + (expires_delta if expires_delta else timedelta(minutes=expire_minutes))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode, verify signature and validate claims of an access token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or tampered authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token type
    token_type = payload.get("type")
    if token_type and token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload
