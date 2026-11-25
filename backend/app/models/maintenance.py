from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class MaintenancePriority(Base):
    __tablename__ = "maintenance_priorities"

    priority_id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.asset_id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.inspection_id", ondelete="CASCADE"), nullable=True, index=True)
    suggested_priority = Column(String(50), nullable=False)
    final_priority = Column(String(50), nullable=True)
    provisional = Column(Boolean, nullable=False, default=True)
    factors_json = Column(Text, nullable=True)
    flags_json = Column(Text, nullable=True)
    rules_version = Column(String(50), nullable=True)
    rules_sha256 = Column(String(64), nullable=True)
    status = Column(String(50), nullable=False, default="suggested")  # "suggested", "confirmed", "overridden", "superseded"
    reviewed_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    asset = relationship("InfrastructureAsset")
    inspection = relationship("Inspection")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    tasks = relationship("MaintenanceTask", back_populates="priority_rel")


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"

    task_id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("infrastructure_assets.asset_id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.inspection_id", ondelete="SET NULL"), nullable=True, index=True)
    priority_id = Column(Integer, ForeignKey("maintenance_priorities.priority_id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False)  # "repair", "further_inspection", "monitoring", "engineering_review"
    priority = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="open", index=True)  # "open", "assigned", "in_progress", "completed", "verified", "cancelled"
    assigned_to = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    due_date = Column(Date, nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    follow_up_inspection_id = Column(Integer, ForeignKey("inspections.inspection_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    asset = relationship("InfrastructureAsset")
    inspection = relationship("Inspection", foreign_keys=[inspection_id])
    priority_rel = relationship("MaintenancePriority", back_populates="tasks", foreign_keys=[priority_id])
    assignee = relationship("User", foreign_keys=[assigned_to])
    creator = relationship("User", foreign_keys=[created_by])
    follow_up_inspection = relationship("Inspection", foreign_keys=[follow_up_inspection_id])
    events = relationship("MaintenanceTaskEvent", back_populates="task", cascade="all, delete-orphan")


class MaintenanceTaskEvent(Base):
    __tablename__ = "maintenance_task_events"

    event_id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("maintenance_tasks.task_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(50), nullable=False)  # "status_change", "assignment", "edit", "comment"
    old_value = Column(String(100), nullable=True)
    new_value = Column(String(100), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("MaintenanceTask", back_populates="events")
    user = relationship("User")
