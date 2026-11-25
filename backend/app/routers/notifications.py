from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    PreferenceResponse,
    PreferenceUpdateRequest,
    SweepResponse,
    UnreadCountResponse,
)
from app.services.notification_service import (
    get_or_create_preference,
    sweep_deadlines_and_overdue,
)

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


# 1. GET /notifications - List user's notifications
@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve notifications addressed to the current authenticated user."""
    query = db.query(Notification).filter(Notification.user_id == current_user.user_id)

    if unread_only:
        query = query.filter(Notification.read_at == None)

    total = query.count()
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.user_id, Notification.read_at == None)
        .count()
    )

    items = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return NotificationListResponse(
        items=items,
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
    )


# 2. GET /notifications/unread-count - Rapid polling endpoint for navbar bell
@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return count of unread notifications for badge counter."""
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.user_id, Notification.read_at == None)
        .count()
    )
    return UnreadCountResponse(unread_count=count)


# 3. POST /notifications/{id}/read - Mark single notification as read
@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a specific notification as read."""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.user_id)
        .first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification #{notification_id} not found.",
        )

    if not notification.read_at:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)

    return notification


# 4. POST /notifications/read-all - Mark all user notifications as read
@router.post("/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all unread notifications for the current user as read."""
    now = datetime.now(timezone.utc)
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.user_id, Notification.read_at == None)
        .update({"read_at": now}, synchronize_session=False)
    )
    db.commit()
    return {"marked_read": count}


# 5. GET /notifications/preferences - Retrieve user preferences
@router.get("/preferences", response_model=PreferenceResponse)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve delivery preferences for current user."""
    pref = get_or_create_preference(db, current_user.user_id)
    return pref


# 6. PUT /notifications/preferences - Update user preferences
@router.put("/preferences", response_model=PreferenceResponse)
def update_preferences(
    update_data: PreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update email and in-app notification preferences."""
    pref = get_or_create_preference(db, current_user.user_id)

    if update_data.in_app_enabled is not None:
        pref.in_app_enabled = update_data.in_app_enabled
    if update_data.email_enabled is not None:
        pref.email_enabled = update_data.email_enabled
    if update_data.min_severity is not None:
        valid_sevs = ["none", "low", "medium", "high", "critical"]
        if update_data.min_severity.lower() in valid_sevs:
            pref.min_severity = update_data.min_severity.lower()

    db.commit()
    db.refresh(pref)
    return pref


# 7. POST /notifications/sweep - Trigger background deadline & overdue check
@router.post("/sweep", response_model=SweepResponse)
def trigger_notification_sweep(
    current_user: User = Depends(require_roles("admin", "civil_engineer", "manager")),
    db: Session = Depends(get_db),
):
    """Check for approaching maintenance task deadlines and overdue inspections."""
    res = sweep_deadlines_and_overdue(db)
    return SweepResponse(**res)
