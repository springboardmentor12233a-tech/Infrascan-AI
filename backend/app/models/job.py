from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_type = Column(String(50), nullable=False, index=True)  # analysis_run, report_generation, batch_import
    payload_json = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="pending", index=True)  # pending, running, completed, failed, cancelled
    progress = Column(Integer, nullable=False, default=0)  # 0 to 100
    result_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retries = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
