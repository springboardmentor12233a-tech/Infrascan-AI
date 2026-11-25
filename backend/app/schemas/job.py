from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    job_type: str = Field(..., description="Type of job: analysis_run, report_generation, batch_import")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Job parameters payload")
    max_retries: int = Field(3, ge=0, le=10)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: str
    status: str
    progress: int
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retries: int
    max_retries: int
    user_id: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int
