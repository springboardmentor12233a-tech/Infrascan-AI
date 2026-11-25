from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Event(Base):
    __tablename__ = "events"

    event_id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    type = Column(String(100), nullable=False, index=True)  # e.g., inspection.created, analysis.completed
    entity_type = Column(String(50), nullable=False)        # e.g., inspection, image, task
    entity_id = Column(String(100), nullable=False)
    audience_json = Column(JSONB().with_variant(JSON, "sqlite"), nullable=False)
    payload_json = Column(JSONB().with_variant(JSON, "sqlite"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "type": self.type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "audience": self.audience_json,
            "payload": self.payload_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EventTicket(Base):
    __tablename__ = "event_tickets"

    ticket_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
