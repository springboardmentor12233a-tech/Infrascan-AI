from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func
from app.database import Base


class DemoMarker(Base):
    __tablename__ = "demo_markers"

    marker_id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # "asset", "inspection", "image", "analysis_run", "task", etc.
    entity_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
