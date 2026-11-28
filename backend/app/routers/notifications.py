"""
app/routers/notifications.py – Notifications and Alerts API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.notification import Notification, AlertLevel
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationOut
from app.core.deps import get_current_user

router = APIRouter(tags=["Notifications"])


@router.get("/", response_model=List[NotificationOut])
def list_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns alerts relevant to the current user (either user-specific or targeting their role).
    """
    role_name = current_user.role.name if current_user.role else ""
    query = db.query(Notification).filter(
        or_(
            Notification.user_id == current_user.id,
            Notification.target_role == role_name,
            Notification.target_role == None
        )
    )
    if unread_only:
        query = query.filter(Notification.is_read == False)

    return query.order_by(Notification.created_at.desc()).limit(50).all()


@router.post("/", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dispatches a new notification / alert."""
    notif = Notification(
        user_id=payload.user_id,
        target_role=payload.target_role,
        title=payload.title,
        message=payload.message,
        alert_level=payload.alert_level or AlertLevel.INFORMATIONAL,
        link=payload.link,
        is_read=False
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/{notif_id}/read", response_model=NotificationOut)
@router.patch("/{notif_id}/read", response_model=NotificationOut)
def mark_as_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks a single alert as read."""
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/read-all")
@router.post("/read-all")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks all user alerts as read."""
    role_name = current_user.role.name if current_user.role else ""
    db.query(Notification).filter(
        or_(
            Notification.user_id == current_user.id,
            Notification.target_role == role_name
        )
    ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"message": "All notifications marked as read"}
