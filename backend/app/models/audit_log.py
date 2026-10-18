"""
models/audit_log.py – records every important action in the system.

This gives administrators a trail of who did what and when.
Examples of logged actions:
  - "register"  on entity "user"
  - "login"     on entity "user"
  - "create"    on entity "asset"
  - "update"    on entity "inspection"
  - "delete"    on entity "asset"
"""

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Who performed the action (nullable because system actions may have no user)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # What happened, e.g. "login", "create", "update", "delete"
    action: Mapped[str] = mapped_column(String(50), nullable=False)

    # Which type of object was affected, e.g. "user", "asset", "inspection"
    entity: Mapped[str] = mapped_column(String(100), nullable=False)

    # The primary key of the affected object (stored as string to be generic)
    entity_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="audit_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} user_id={self.user_id} "
            f"action={self.action!r} entity={self.entity!r}>"
        )
