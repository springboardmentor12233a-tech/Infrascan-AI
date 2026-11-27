from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class InspectionReport(Base):
    __tablename__ = "inspection_reports"
    __table_args__ = {"extend_existing": True}

    report_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("inspections.inspection_id", ondelete="CASCADE"), nullable=False, index=True)
    generated_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    report_format = Column(String(10), nullable=False, default="pdf")  # pdf, csv, json, xlsx
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    summary_findings = Column(Text, nullable=True)
    overall_condition_score = Column(Float, nullable=False, default=85.0)  # 0 to 100
    engineer_signoff = Column(Boolean, nullable=False, default=False)
    signoff_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    inspection = relationship("Inspection", backref="reports")
    generator = relationship("User", backref="generated_reports")
