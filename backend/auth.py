
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from pwdlib import PasswordHash

from database import get_connection


# JWT Configuration
SECRET_KEY = os.getenv("INFRASCAN_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "INFRASCAN_SECRET_KEY environment variable is not configured."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()

VALID_ROLES = {
    "Admin",
    "User",
}


# Password Functions
def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


# JWT Token Functions
def create_access_token(user_id: int, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expires_at,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# User Authentication
def authenticate_user(email: str, password: str):
    connection = get_connection()

    try:
        user = connection.execute(
            """
            SELECT id, full_name, email, hashed_password, role, is_active
            FROM users
            WHERE email = ?
            """,
            (email.lower().strip(),),
        ).fetchone()

        if not user or not user["is_active"]:
            return None

        if not verify_password(password, user["hashed_password"]):
            return None

        return {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
        }

    finally:
        connection.close()


def get_user_by_id(user_id: int):
    connection = get_connection()

    try:
        user = connection.execute(
            """
            SELECT id, full_name, email, role, is_active
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        if not user or not user["is_active"]:
            return None

        return dict(user)

    finally:
        connection.close()


# Authentication Router
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


class LoginRequest(BaseModel):
    email: str
    password: str


# Login API
@router.post("/login")
def login(request: LoginRequest):
    user = authenticate_user(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    token = create_access_token(user["id"], user["role"])

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


# Authentication Security
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = int(payload.get("sub"))

    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User account not found or inactive",
        )

    return user


# Role-Based Access Control
def require_role(*allowed_roles: str):
    def role_checker(
        current_user: dict = Depends(get_current_user),
    ):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource",
            )

        return current_user

    return role_checker


# Get Current Logged-In User
@router.get("/me")
def read_current_user(
    current_user: dict = Depends(get_current_user),
):
    return {
        "message": "User authenticated successfully",
        "user": current_user,
    }


# Get All Users - Admin Only
@router.get("/users")
def get_all_users(
    current_user: dict = Depends(require_role("Admin")),
):
    connection = get_connection()

    try:
        users = connection.execute(
            """
            SELECT id, full_name, email, role, is_active, created_at
            FROM users
            ORDER BY created_at DESC
            """
        ).fetchall()

        return {
            "total": len(users),
            "users": [dict(user) for user in users],
        }

    finally:
        connection.close()


# Activate or Deactivate User - Admin Only
@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: dict = Depends(require_role("Admin")),
):
    connection = get_connection()

    try:
        user = connection.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        # Admin cannot deactivate their own account
        if user["id"] == current_user["id"] and not is_active:
            raise HTTPException(
                status_code=400,
                detail="You cannot deactivate your own account",
            )

        connection.execute(
            """
            UPDATE users
            SET is_active = ?
            WHERE id = ?
            """,
            (int(is_active), user_id),
        )

        connection.commit()

        return {
            "message": (
                "User activated successfully"
                if is_active
                else "User deactivated successfully"
            ),
            "user_id": user_id,
            "is_active": is_active,
        }

    finally:
        connection.close()


# Change Password
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    connection = get_connection()

    try:
        user = connection.execute(
            """
            SELECT hashed_password
            FROM users
            WHERE id = ?
            """,
            (current_user["id"],),
        ).fetchone()

        if not user or not verify_password(
            request.current_password,
            user["hashed_password"],
        ):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect",
            )

        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="New password must contain at least 8 characters",
            )

        connection.execute(
            """
            UPDATE users
            SET hashed_password = ?
            WHERE id = ?
            """,
            (
                hash_password(request.new_password),
                current_user["id"],
            ),
        )

        connection.commit()

        return {
            "message": "Password changed successfully"
        }

    finally:
        connection.close()
