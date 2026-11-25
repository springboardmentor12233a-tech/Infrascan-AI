"""
InfraScan Authentication & Cryptography Service.

Provides:
- Secure password hashing using PBKDF2-HMAC-SHA256 (100,000 iterations) with 16-byte random salt.
- Constant-time password verification to prevent timing attacks.
- JWT Access Token generation and validation (HS256).
- Cryptographically secure password reset token generation.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

import jwt

# Configuration (defaults to strong internal secret; can be overridden via ENV)
SECRET_KEY = os.getenv("INFRASCAN_SECRET_KEY", "infrascan-civil-ai-secret-key-production-2026-v2")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
RESET_TOKEN_EXPIRE_HOURS = 1


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hashes a plain password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    
    Args:
        password: Plain text password.
        salt: Optional 32-character hex salt. If None, a new random salt is generated.
        
    Returns:
        Tuple of (hex_hashed_password, hex_salt).
    """
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()
    return hashed, salt


def verify_password(plain_password: str, hashed_password: str, salt: str) -> bool:
    """
    Verifies a plain password against stored hash using constant-time comparison.
    """
    new_hash, _ = hash_password(plain_password, salt)
    return secrets.compare_digest(new_hash, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a signed JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes and validates a JWT token. Returns payload dict or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None


def generate_reset_token() -> str:
    """Generates a URL-safe, cryptographically secure 32-byte hex reset token."""
    return secrets.token_urlsafe(32)
