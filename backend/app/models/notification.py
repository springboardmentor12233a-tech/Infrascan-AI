"""
models/notification.py – In-app alerts and notifications for infrastructure safety findings.
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AlertLevel(str, enum.Enum):
    INFORMATIONAL = "Informational"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    target_role: Mapped[str | None] = mapped_column(String(50), nullable=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    alert_level: Mapped[AlertLevel] = mapped_column(
        Enum(AlertLevel, name="alert_level_enum"),
        default=AlertLevel.INFORMATIONAL,
        nullable=False
    )
    link: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["User | None"] = relationship("User")  # type: ignore[name-defined]
