from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MaintenanceTaskCreate(BaseModel):
    asset_id: int
    inspection_id: Optional[int] = None
    priority_id: Optional[int] = None
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    task_type: str = Field("repair", description="repair, further_inspection, monitoring, engineering_review")
    priority: str = Field("medium", description="routine_monitoring, low, medium, high, urgent_engineering_review, P1, P2, P3, P4")
    assigned_to: Optional[int] = None
    due_date: Optional[date] = None


class MaintenanceTaskStatusUpdate(BaseModel):
    status: str = Field(..., description="open, assigned, in_progress, completed, verified, cancelled")
    notes: Optional[str] = None


class MaintenanceTaskVerifyRequest(BaseModel):
    verified: bool = True
    comment: Optional[str] = None


class MaintenancePriorityConfirmRequest(BaseModel):
    final_priority: str
    comment: Optional[str] = None


class MaintenanceTaskResponse(BaseModel):
    task_id: int
    asset_id: int
    asset_name: Optional[str] = None
    inspection_id: Optional[int] = None
    priority_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    task_type: str
    priority: str
    status: str
    assigned_to: Optional[int] = None
    assignee_name: Optional[str] = None
    created_by: Optional[int] = None
    due_date: Optional[date] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaintenancePriorityResponse(BaseModel):
    priority_id: int
    asset_id: int
    inspection_id: Optional[int] = None
    suggested_priority: str
    final_priority: Optional[str] = None
    provisional: bool
    status: str
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
