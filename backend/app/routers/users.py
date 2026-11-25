import csv
import io
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.audit_log import AuditLog
from app.models.user import ALLOWED_ROLES, User
from app.schemas.user import (
    AdminCreateUserRequest,
    AuditLogResponse,
    ChangePasswordRequest,
    PaginatedAuditLogsResponse,
    PaginatedUsersResponse,
    UpdateActiveRequest,
    UpdateRoleRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.audit import create_audit_log
from app.services.security import (
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.services.session_service import create_password_reset_token, revoke_user_sessions
from app.services.event_service import publish

router = APIRouter(prefix="", tags=["Users & Administration"])


# --- Current User Profile Endpoints ---


@router.get("/users/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Retrieve profile of the currently authenticated user."""
    return current_user


@router.put("/users/me", response_model=UserResponse)
def update_my_profile(
    update_data: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update full name of the currently authenticated user."""
    old_name = current_user.full_name
    current_user.full_name = update_data.full_name.strip()
    db.commit()
    db.refresh(current_user)

    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="profile_update",
        user_id=current_user.user_id,
        entity_type="user",
        entity_id=str(current_user.user_id),
        ip_address=client_ip,
    )
    return current_user


@router.post("/users/me/change-password")
def change_my_password(
    password_data: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for currently authenticated user, revoking all other sessions."""
    client_ip = request.client.host if request.client else None

    # Verify old password
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password does not match",
        )

    # Validate new password against policy
    validate_password_policy(password_data.new_password)

    # Hash and save new password
    current_user.password_hash = hash_password(password_data.new_password)

    # Revoke sessions for this user so other devices must re-authenticate
    revoke_user_sessions(db, current_user.user_id)
    db.commit()

    create_audit_log(
        db=db,
        action="password_change",
        user_id=current_user.user_id,
        entity_type="user",
        entity_id=str(current_user.user_id),
        ip_address=client_ip,
    )
    return {"message": "Password changed successfully. Other active sessions have been signed out."}


# --- Inspector Selection Dropdown ---


@router.get("/users/inspectors", response_model=List[UserResponse])
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


# --- Admin User Management Endpoints ---


@router.get("/users", response_model=PaginatedUsersResponse)
def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """List and search all registered users with filters and pagination (Admin only)."""
    query = db.query(User)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(or_(User.full_name.ilike(s), User.email.ilike(s)))
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    items = query.order_by(User.user_id.asc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedUsersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    data: AdminCreateUserRequest,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Create a user with an assigned role directly (Admin only)."""
    if data.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Allowed roles: {', '.join(ALLOWED_ROLES)}",
        )

    validate_password_policy(data.password)

    email = data.email.lower().strip()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    new_user = User(
        full_name=data.full_name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="admin_create_user",
        user_id=admin.user_id,
        entity_type="user",
        entity_id=str(new_user.user_id),
        ip_address=client_ip,
    )
    return new_user


@router.put("/users/{id}/role", response_model=UserResponse)
def update_user_role(
    id: int,
    role_data: UpdateRoleRequest,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Update a user's role (Admin only). Protects the last active administrator."""
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

    # Protect last active admin from demotion
    if user.role == "admin" and role_data.role != "admin" and user.is_active:
        active_admins = db.query(User).filter(User.role == "admin", User.is_active == True).count()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last active administrator.",
            )

    old_role = user.role
    user.role = role_data.role
    publish(
        db=db,
        event_type="user.role_changed",
        entity_type="user",
        entity_id=user.user_id,
        audience={"user_ids": [user.user_id], "roles": ["admin"]},
        payload={"user_id": user.user_id, "old_role": old_role, "new_role": user.role},
    )
    db.commit()
    db.refresh(user)

    create_audit_log(
        db=db,
        action="role_change",
        user_id=admin.user_id,
        entity_type="user",
        entity_id=f"{user.user_id}: {old_role} -> {user.role}",
        ip_address=client_ip,
    )
    return user


@router.put("/users/{id}/active", response_model=UserResponse)
def update_user_active_status(
    id: int,
    active_data: UpdateActiveRequest,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Activate or deactivate a user account (Admin only). Protects last active admin and self-deactivation."""
    client_ip = request.client.host if request.client else None

    user = db.query(User).filter(User.user_id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent admin self-deactivation
    if admin.user_id == user.user_id and not active_data.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own account.",
        )

    # Protect last active admin from deactivation
    if user.role == "admin" and not active_data.is_active and user.is_active:
        active_admins = db.query(User).filter(User.role == "admin", User.is_active == True).count()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active administrator.",
            )

    user.is_active = active_data.is_active
    if not active_data.is_active:
        revoke_user_sessions(db, user.user_id)
    db.commit()
    db.refresh(user)

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


@router.post("/users/{id}/force-reset")
def force_password_reset(
    id: int,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Generate a single-use password reset token for a user (Admin only)."""
    user = db.query(User).filter(User.user_id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    raw_token = create_password_reset_token(db, user.user_id)
    revoke_user_sessions(db, user.user_id)

    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="admin_force_password_reset",
        user_id=admin.user_id,
        entity_type="user",
        entity_id=str(user.user_id),
        ip_address=client_ip,
    )
    return {
        "message": "Password reset token generated and existing sessions revoked.",
        "reset_token": raw_token,
    }


@router.delete("/users/{id}/sessions")
def admin_revoke_user_sessions(
    id: int,
    request: Request,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Revoke all active sessions of a specified user (Admin only)."""
    user = db.query(User).filter(User.user_id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    count = revoke_user_sessions(db, user.user_id)
    publish(
        db=db,
        event_type="user.session_revoked",
        entity_type="user",
        entity_id=user.user_id,
        audience={"user_ids": [user.user_id], "roles": ["admin"]},
        payload={"user_id": user.user_id, "revoked_count": count},
    )
    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="admin_revoke_sessions",
        user_id=admin.user_id,
        entity_type="user",
        entity_id=f"{user.user_id} ({count} sessions)",
        ip_address=client_ip,
    )
    return {"message": f"Successfully revoked {count} sessions for user {user.email}"}


@router.get("/users/{id}/audit-logs", response_model=List[AuditLogResponse])
def get_user_recent_audit_logs(
    id: int,
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """View a user's recent audit entries (Admin only)."""
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return logs


# --- Global Admin Audit Log Endpoints ---


@router.get("/audit-logs", response_model=PaginatedAuditLogsResponse)
def list_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Query audit logs with filtering and pagination (Admin only)."""
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)

    total = query.count()
    items = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedAuditLogsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/audit-logs/export")
def export_audit_logs_csv(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Export filtered audit logs as CSV file (Admin only). Includes formula injection protection."""
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    logs = query.order_by(AuditLog.created_at.desc()).limit(5000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["log_id", "user_id", "action", "entity_type", "entity_id", "ip_address", "created_at"])

    # Protect against CSV formula injection: prefix =, +, -, @ with an apostrophe
    def sanitize(val):
        if val is None:
            return ""
        s = str(val)
        if s.startswith(("=", "+", "-", "@")):
            return "'" + s
        return s

    for l in logs:
        writer.writerow([
            l.log_id,
            l.user_id,
            sanitize(l.action),
            sanitize(l.entity_type),
            sanitize(l.entity_id),
            sanitize(l.ip_address),
            l.created_at.isoformat() if l.created_at else "",
        ])

    csv_data = "\ufeff" + output.getvalue()  # UTF-8 with BOM
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
