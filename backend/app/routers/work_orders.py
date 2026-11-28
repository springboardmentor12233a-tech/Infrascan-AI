"""
app/routers/work_orders.py – Maintenance Work Order Management API
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderPriority
from app.models.infrastructure_asset import InfrastructureAsset
from app.models.user import User
from app.schemas.work_order import WorkOrderCreate, WorkOrderUpdate, WorkOrderOut
from app.core.deps import get_current_user, require_roles
from app.services.audit import log_action

router = APIRouter(tags=["Work Orders"])


@router.get("/", response_model=List[WorkOrderOut])
def list_work_orders(
    asset_id: Optional[int] = Query(None),
    status: Optional[WorkOrderStatus] = Query(None),
    priority: Optional[WorkOrderPriority] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all maintenance work orders with optional filtering."""
    query = db.query(WorkOrder)
    if asset_id:
        query = query.filter(WorkOrder.asset_id == asset_id)
    if status:
        query = query.filter(WorkOrder.status == status)
    if priority:
        query = query.filter(WorkOrder.priority == priority)

    orders = query.order_by(WorkOrder.created_at.desc()).all()
    results = []
    for wo in orders:
        data = WorkOrderOut.model_validate(wo)
        if wo.asset:
            data.asset_code = wo.asset.asset_code
            data.asset_name = wo.asset.name
        if wo.assigned_to:
            data.assigned_to_name = wo.assigned_to.full_name
        results.append(data)
    return results


@router.post("/", response_model=WorkOrderOut, status_code=status.HTTP_201_CREATED)
def create_work_order(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new maintenance repair work order."""
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == payload.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    wo = WorkOrder(
        asset_id=payload.asset_id,
        inspection_id=payload.inspection_id,
        assigned_to_id=payload.assigned_to_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority or WorkOrderPriority.MEDIUM,
        status=WorkOrderStatus.OPEN,
        estimated_cost=payload.estimated_cost,
        due_date=payload.due_date
    )
    db.add(wo)
    db.commit()
    db.refresh(wo)

    log_action(db, action="create_work_order", entity="work_order", entity_id=str(wo.id), user_id=current_user.id)

    data = WorkOrderOut.model_validate(wo)
    data.asset_code = asset.asset_code
    data.asset_name = asset.name
    if wo.assigned_to:
        data.assigned_to_name = wo.assigned_to.full_name
    return data


@router.put("/{work_order_id}", response_model=WorkOrderOut)
def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates work order status, assignment, resolution notes."""
    wo = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not wo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    update_dict = payload.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(wo, field, val)

    if payload.status == WorkOrderStatus.RESOLVED and not wo.resolved_at:
        wo.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(wo)

    log_action(db, action="update_work_order", entity="work_order", entity_id=str(wo.id), user_id=current_user.id)

    data = WorkOrderOut.model_validate(wo)
    if wo.asset:
        data.asset_code = wo.asset.asset_code
        data.asset_name = wo.asset.name
    if wo.assigned_to:
        data.assigned_to_name = wo.assigned_to.full_name
    return data
