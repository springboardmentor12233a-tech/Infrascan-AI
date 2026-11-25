from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    task = Column(String(50), nullable=False)  # classification, detection, segmentation
    split_stats_json = Column(Text, nullable=False)  # train, val, test image counts
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ModelEvent(Base):
    __tablename__ = "model_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id = Column(String(100), ForeignKey("model_versions.model_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # registered, smoke_tested, activated, rolled_back
    performed_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    model = relationship("ModelVersion")
    performer = relationship("User", foreign_keys=[performed_by])
