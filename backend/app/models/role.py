"""
models/role.py – the Role table.

Roles are seeded once on startup. They never change at runtime.
The 5 roles are:
  1. Administrator
  2. Infrastructure Manager
  3. Civil Engineer
  4. Infrastructure Inspector
  5. Maintenance Engineer
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # One role → many users
    users: Mapped[list["User"]] = relationship("User", back_populates="role")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name!r}>"


# ── Seed data ─────────────────────────────────────────────────────────────────
# These are the exact role names used in permission checks throughout the app.
ROLE_NAMES = [
    "Administrator",
    "Infrastructure Manager",
    "Civil Engineer",
    "Infrastructure Inspector",
    "Maintenance Engineer",
]
