from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.notification import AlertLevel


class NotificationCreate(BaseModel):
    user_id: Optional[int] = None
    target_role: Optional[str] = None
    title: str
    message: str
    alert_level: Optional[AlertLevel] = AlertLevel.INFORMATIONAL
    link: Optional[str] = None


class NotificationOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    target_role: Optional[str] = None
    title: str
    message: str
    alert_level: AlertLevel
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
