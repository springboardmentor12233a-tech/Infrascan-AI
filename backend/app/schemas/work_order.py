from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.work_order import WorkOrderStatus, WorkOrderPriority


class WorkOrderCreate(BaseModel):
    asset_id: int
    inspection_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    title: str
    description: str
    priority: Optional[WorkOrderPriority] = WorkOrderPriority.MEDIUM
    due_date: Optional[date] = None
    estimated_cost: Optional[float] = None


class WorkOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to_id: Optional[int] = None
    priority: Optional[WorkOrderPriority] = None
    status: Optional[WorkOrderStatus] = None
    due_date: Optional[date] = None
    estimated_cost: Optional[float] = None
    resolution_notes: Optional[str] = None


class WorkOrderOut(BaseModel):
    id: int
    asset_id: int
    inspection_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    title: str
    description: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    estimated_cost: Optional[float] = None
    due_date: Optional[date] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    asset_code: Optional[str] = None
    asset_name: Optional[str] = None
    assigned_to_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
