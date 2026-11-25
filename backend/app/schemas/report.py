from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ReportFileResponse(BaseModel):
    file_id: int
    format: str
    path: str
    size: int
    sha256: str

    model_config = ConfigDict(from_attributes=True)


class ReportResponse(BaseModel):
    report_id: int
    inspection_id: int
    version: int
    status: str
    generated_by: int
    generated_at: datetime
    content_sha256: str
    notes: Optional[str] = None
    files: List[ReportFileResponse] = []
    is_final: bool = False

    model_config = ConfigDict(from_attributes=True)


class CreateReportRequest(BaseModel):
    notes: Optional[str] = None


class PaginatedReportsResponse(BaseModel):
    items: List[ReportResponse]
    total: int
    page: int
    page_size: int
