"""
services/seed.py – creates the 5 roles the first time the app starts.

This is called once at startup (inside main.py). It uses a simple
"does this role name exist already?" check so it is safe to run every time
without creating duplicates.

More seed data (users, sample assets) is added in Phase 7.
"""

from sqlalchemy.orm import Session

from app.models.role import Role, ROLE_NAMES


def seed_roles(db: Session) -> None:
    """Insert the 5 roles if they don't exist yet."""
    for name in ROLE_NAMES:
        exists = db.query(Role).filter(Role.name == name).first()
        if not exists:
            db.add(Role(name=name))
    db.commit()
    print(f"[DB] Roles seeded: {ROLE_NAMES}")
