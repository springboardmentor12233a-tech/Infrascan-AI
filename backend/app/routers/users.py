from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.user import ALLOWED_ROLES, User
from app.schemas.user import (
    ChangePasswordRequest,
    UpdateActiveRequest,
    UpdateRoleRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.audit import create_audit_log
from app.services.security import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Retrieve profile of the currently authenticated user."""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update full name of the currently authenticated user."""
    current_user.full_name = update_data.full_name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/change-password")
def change_my_password(
    password_data: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for currently authenticated user."""
    client_ip = request.client.host if request.client else None

    # Verify old password
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password does not match",
        )

    # Hash and save new password
    current_user.password_hash = hash_password(password_data.new_password)
    db.commit()

    # Record audit log
    create_audit_log(
        db=db,
        action="password_change",
        user_id=current_user.user_id,
        entity_type="user",
        entity_id=str(current_user.user_id),
        ip_address=client_ip,
    )

    return {"message": "Password changed successfully"}


# --- Inspector selection endpoint ---


@router.get("/inspectors", response_model=List[UserResponse])
def list_inspectors(
    current_user: User = Depends(require_roles("admin", "manager", "civil_engineer")),
    db: Session = Depends(get_db),
):
    """List all active users with the inspector role (for assignment dropdowns)."""
    inspectors = (
        db.query(User)
        .filter(User.role == "inspector", User.is_active == True)
        .order_by(User.full_name.asc())
        .all()
    )
    return inspectors


# --- Admin Only Endpoints ---


@router.get("", response_model=List[UserResponse])
def list_users(
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """List all registered users (Admin only)."""
    users = db.query(User).order_by(User.user_id.asc()).all()
    return users


@router.put("/{id}/role", response_model=UserResponse)
def update_user_role(
    id: int,
    role_data: UpdateRoleRequest,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Update a user's role (Admin only)."""
    client_ip = request.client.host if request.client else None

    if role_data.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Allowed roles: {', '.join(ALLOWED_ROLES)}",
        )

    user = db.query(User).filter(User.user_id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.role = role_data.role
    db.commit()
    db.refresh(user)

    # Record audit log
    create_audit_log(
        db=db,
        action="role_change",
        user_id=admin.user_id,
        entity_type="user",
        entity_id=str(user.user_id),
        ip_address=client_ip,
    )

    return user


@router.put("/{id}/active", response_model=UserResponse)
def update_user_active_status(
    id: int,
    active_data: UpdateActiveRequest,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Activate or deactivate a user account (Admin only)."""
    client_ip = request.client.host if request.client else None

    user = db.query(User).filter(User.user_id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = active_data.is_active
    db.commit()
    db.refresh(user)

    # Record audit log
    action = "account_activated" if active_data.is_active else "account_deactivated"
    create_audit_log(
        db=db,
        action=action,
        user_id=admin.user_id,
        entity_type="user",
        entity_id=str(user.user_id),
        ip_address=client_ip,
    )

    return user
