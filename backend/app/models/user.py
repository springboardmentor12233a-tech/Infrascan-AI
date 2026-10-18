"""
models/user.py – the User table.

Each user has:
  - a unique email address
  - a bcrypt-hashed password (never store plain text!)
  - a role (foreign key → roles table)
  - an active flag so we can deactivate without deleting
"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    full_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # unique=True means two users can't share an email
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # We NEVER store the real password – only the bcrypt hash
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Foreign key to roles table
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id"), nullable=False
    )

    # Active users can log in; inactive users cannot
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # server_default means the DB sets this automatically when a row is inserted
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    role: Mapped["Role"] = relationship("Role", back_populates="users")  # type: ignore[name-defined]
    inspections: Mapped[list["Inspection"]] = relationship(  # type: ignore[name-defined]
        "Inspection", back_populates="inspector", foreign_keys="Inspection.inspector_id"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # type: ignore[name-defined]
        "AuditLog", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role_id={self.role_id}>"
