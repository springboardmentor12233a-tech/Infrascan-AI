import os
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .db import get_db
from .models import User

SECRET = os.getenv("INFRASCAN_SECRET", "local-demo-secret-change-me-please-set-a-production-secret")
bearer = HTTPBearer(auto_error=False)

def hash_password(value: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), salt, 310_000)
    return "pbkdf2_sha256$310000${}${}".format(
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )

def verify_password(value: str, hashed: str) -> bool:
    if not hashed or not value:
        return False
    if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
        import bcrypt
        try:
            return bcrypt.checkpw(value.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False
    try:
        algorithm, rounds, encoded_salt, encoded_digest = hashed.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, Exception):
        return False

def make_token(user: User) -> str:
    user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
    return jwt.encode({"sub": user.email, "role": user.role, "user_id": user_id, "exp": datetime.now(timezone.utc) + timedelta(hours=12)}, SECRET, algorithm="HS256")

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        try:
            payload = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"])
        except jwt.PyJWTError:
            from app.config import settings
            payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        sub = payload["sub"]
        if "@" in str(sub):
            user = db.query(User).filter(User.email == str(sub)).first()
        else:
            try:
                user = db.get(User, int(sub))
            except ValueError:
                user = db.query(User).filter(User.email == str(sub)).first()
    except (jwt.PyJWTError, KeyError, ValueError):
        user = None
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user
