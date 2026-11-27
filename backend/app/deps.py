from typing import Callable, Optional
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.security import decode_access_token

# OAuth2 scheme looking for Bearer token at /auth/login (auto_error=False allows query token fallback for file downloads)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    header_token: Optional[str] = Depends(oauth2_scheme),
    query_token: Optional[str] = Query(None, alias="token"),
    db: Session = Depends(get_db),
) -> User:
    """Validate JWT token from Authorization header or URL query parameter and return active user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = header_token or query_token
    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except (jwt.PyJWTError, Exception):
        raise credentials_exception

    if "@" in str(sub):
        user = db.query(User).filter(User.email == str(sub)).first()
    else:
        try:
            uid = int(sub)
            user = db.query(User).filter(User.user_id == uid).first()
        except ValueError:
            user = db.query(User).filter(User.email == str(sub)).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    return user


def require_roles(*allowed_roles: str) -> Callable:
    """Dependency factory that checks if current user has one of the allowed roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker
