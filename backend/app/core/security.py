"""
core/security.py – low-level security helpers.

Two responsibilities:
  1. Password hashing with bcrypt (via passlib)
  2. JWT creation and verification (via python-jose)

Nothing in this file knows about FastAPI or the database.
That separation makes it easy to test in isolation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────
# bcrypt is the industry standard for hashing passwords.
# deprecated="auto" means old hashes will be upgraded transparently.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Turn a plain-text password into a bcrypt hash."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plain password matches the stored hash."""
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────
# A JWT is a signed token we give to the user after login.
# The user sends it back with every request so we know who they are.
# We put the user's ID ("sub") and role inside the token payload.

def create_access_token(data: dict[str, Any]) -> str:
    """
    Create a signed JWT that expires after ACCESS_TOKEN_EXPIRE_MINUTES.

    Args:
        data: dict with at minimum {"sub": "<user_id>", "role": "<role_name>"}

    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT.

    Raises:
        JWTError if the token is invalid, expired, or tampered with.

    Returns:
        The payload dict (e.g. {"sub": "3", "role": "Administrator", "exp": ...})
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# Re-export JWTError so callers only need to import from this module
__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "JWTError",
]
