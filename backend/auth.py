import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User

# Configuration
ENV_MODE = os.environ.get("INFRASCAN_ENV", "development").lower()
SECRET_KEY = os.environ.get("INFRASCAN_JWT_SECRET")

KNOWN_PLACEHOLDERS = {
    "replace_with_strong_random_jwt_secret_key_exceeding_32_chars!",
    "infrascan_prod_jwt_secret_key_exceeding_32_characters_2026!",
    "dev_insecure_jwt_secret_for_local_development_only_replace_in_prod",
    "CHANGEME_GENERATE_A_SECURE_RANDOM_SECRET_KEY",
    "CHANGEME_GENERATE_A_SECURE_RANDOM_SECRET_KEY_MIN_32_CHARS",
}

if ENV_MODE == "production":
    if not SECRET_KEY or not SECRET_KEY.strip():
        raise RuntimeError(
            "FATAL [Production Startup Blocked]: INFRASCAN_JWT_SECRET is unset or empty.\n"
            "Production deployments require a secure random JWT secret key.\n"
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    if len(SECRET_KEY.strip()) < 32:
        raise RuntimeError(
            f"FATAL [Production Startup Blocked]: INFRASCAN_JWT_SECRET is too short ({len(SECRET_KEY.strip())} characters).\n"
            "Production security strictly requires a secret key of at least 32 characters.\n"
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    cleaned = SECRET_KEY.strip().lower()
    is_placeholder = (
        SECRET_KEY.strip() in KNOWN_PLACEHOLDERS
        or any(token in cleaned for token in ["replace_with", "changeme", "placeholder", "dev_insecure", "secret_key_exceeding", "your_secret_here"])
    )
    if is_placeholder:
        raise RuntimeError(
            "FATAL [Production Startup Blocked]: INFRASCAN_JWT_SECRET contains a known placeholder value.\n"
            "Never use template or placeholder secrets in production.\n"
            "Generate a fresh random secret with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
else:
    # Explicit development mode secret with warning
    if not SECRET_KEY:
        SECRET_KEY = "dev_insecure_jwt_secret_for_local_development_only_replace_in_prod"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or session expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact a system administrator."
        )

    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access this resource."
        )
    return current_user
