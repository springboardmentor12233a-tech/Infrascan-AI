from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    title: str,
    message: str,
    severity: str = "info",
    user_id: Optional[int] = None,
    link: Optional[str] = None,
) -> Notification:
    """Create a system or targeted notification/alert."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        severity=severity,
        link=link,
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def get_user_notifications(
    db: Session,
    user_id: Optional[int] = None,
    unread_only: bool = False,
    limit: int = 50,
) -> List[Notification]:
    """Retrieve notifications for a user or broadcast alerts."""
    query = db.query(Notification)
    if user_id:
        query = query.filter((Notification.user_id == user_id) | (Notification.user_id == None))
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


def mark_notification_read(
    db: Session,
    notification_id: int,
    user_id: Optional[int] = None,
) -> Optional[Notification]:
    """Mark a notification as read."""
    notif = db.query(Notification).filter(Notification.notification_id == notification_id).first()
    if notif:
        notif.is_read = True
        db.commit()
        db.refresh(notif)
    return notif
