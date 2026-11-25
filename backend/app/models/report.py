from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    inspection_id = Column(Integer, ForeignKey("inspections.inspection_id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default="draft")  # "draft" | "final"
    generated_by = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    content_sha256 = Column(String(64), nullable=False)
    snapshot_json_path = Column(String(500), nullable=False)
    model_versions_json = Column(Text, nullable=True)
    rules_versions_json = Column(Text, nullable=True)
    review_summary_json = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    files = relationship("ReportFile", backref="report", cascade="all, delete-orphan")

    @property
    def is_final(self) -> bool:
        return self.status == "final"


class ReportFile(Base):
    __tablename__ = "report_files"

    file_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.report_id", ondelete="CASCADE"), nullable=False, index=True)
    format = Column(String(20), nullable=False)  # "pdf", "csv", "xlsx", "json"
    path = Column(String(500), nullable=False)
    size = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
