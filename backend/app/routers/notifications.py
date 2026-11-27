from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import (
    create_notification,
    get_user_notifications,
    mark_notification_read,
)


router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


class NotificationCreateRequest(BaseModel):
    title: str
    message: str
    severity: str = "info"  # info, low, medium, high, critical
    link: Optional[str] = None
    user_id: Optional[int] = None


@router.get("")
def list_notifications(
    unread_only: bool = Query(False, description="Filter unread alerts only"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve in-app notifications and critical inspection alerts."""
    notifs = get_user_notifications(db=db, user_id=current_user.user_id, unread_only=unread_only)
    return [
        {
            "notification_id": n.notification_id,
            "title": n.title,
            "message": n.message,
            "severity": n.severity,
            "link": n.link,
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in notifs
    ]


@router.put("/{notification_id}/read")
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    notif = mark_notification_read(db=db, notification_id=notification_id, user_id=current_user.user_id)
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {"message": "Notification marked as read", "notification_id": notification_id}


@router.post("", status_code=status.HTTP_201_CREATED)
def post_notification(
    payload: NotificationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "civil_engineer")),
):
    """Dispatch a new notification or broadcast alert."""
    notif = create_notification(
        db=db,
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        user_id=payload.user_id,
        link=payload.link,
    )
    return {
        "notification_id": notif.notification_id,
        "title": notif.title,
        "severity": notif.severity,
        "created_at": notif.created_at,
    }
