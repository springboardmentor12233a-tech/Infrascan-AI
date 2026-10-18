from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserOut, UserRoleUpdate
from app.core.deps import require_roles, get_current_user
from app.services.audit import log_action

router = APIRouter(tags=["Users"])


@router.get("/", response_model=List[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles("Administrator"))
):
    """Admin-only: list all registered users."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/inspectors", response_model=List[UserOut])
def list_inspectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List users eligible to be assigned as inspectors."""
    inspector_role = db.query(Role).filter(Role.name == "Infrastructure Inspector").first()
    if not inspector_role:
        return []
    return db.query(User).filter(User.role_id == inspector_role.id, User.is_active == True).all()


@router.put("/{user_id}", response_model=UserOut)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles("Administrator"))
):
    """Admin-only: update user role and active status."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role not found"
        )

    target_user.role_id = payload.role_id
    if payload.is_active is not None:
        target_user.is_active = payload.is_active

    db.commit()
    db.refresh(target_user)

    log_action(
        db,
        action="update_role",
        entity="user",
        entity_id=str(target_user.id),
        user_id=admin_user.id
    )
    return target_user
