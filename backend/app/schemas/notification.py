from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    body: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    read_at: Optional[datetime] = None
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
    created_at: datetime
    is_read: bool = False

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class PreferenceResponse(BaseModel):
    user_id: int
    in_app_enabled: bool
    email_enabled: bool
    min_severity: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PreferenceUpdateRequest(BaseModel):
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    min_severity: Optional[str] = None


class SweepResponse(BaseModel):
    maintenance_alerts: int
    overdue_inspections: int
