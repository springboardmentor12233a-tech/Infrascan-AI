from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import synonym
from ..db import Base

# Allowed user roles in InfraScan
ALLOWED_ROLES = [
    "civil_engineer",
    "inspector",
    "maintenance_engineer",
    "manager",
    "admin",
]


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    id = synonym("user_id")
    full_name = Column(String(100), nullable=False)
    name = synonym("full_name")
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="inspector")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
