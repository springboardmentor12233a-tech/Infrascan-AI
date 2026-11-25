from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.asset import InfrastructureAsset
from app.models.maintenance import MaintenancePriority, MaintenanceTask, MaintenanceTaskEvent
from app.models.user import User
from app.schemas.maintenance import (
    MaintenancePriorityConfirmRequest,
    MaintenancePriorityResponse,
    MaintenanceTaskCreate,
    MaintenanceTaskResponse,
    MaintenanceTaskStatusUpdate,
    MaintenanceTaskVerifyRequest,
)
from app.services.audit import create_audit_log
from app.services.event_service import publish
from app.services.notification_service import create_notification

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


def _format_task_response(task: MaintenanceTask, db: Session) -> MaintenanceTaskResponse:
    asset_name = task.asset.name if task.asset else None
    assignee_name = task.assignee.full_name if task.assignee else None
    return MaintenanceTaskResponse(
        task_id=task.task_id,
        asset_id=task.asset_id,
        asset_name=asset_name,
        inspection_id=task.inspection_id,
        priority_id=task.priority_id,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        assigned_to=task.assigned_to,
        assignee_name=assignee_name,
        created_by=task.created_by,
        due_date=task.due_date,
        started_at=task.started_at,
        completed_at=task.completed_at,
        resolution_notes=task.resolution_notes,
        created_at=task.created_at,
    )


@router.get("/tasks", response_model=List[MaintenanceTaskResponse])
def list_tasks(
    asset_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List maintenance tasks.
    Maintenance engineers only see tasks assigned to them.
    Admins, Managers, and Civil Engineers see all tasks.
    """
    query = db.query(MaintenanceTask)

    if current_user.role == "maintenance_engineer":
        query = query.filter(MaintenanceTask.assigned_to == current_user.user_id)

    if asset_id:
        query = query.filter(MaintenanceTask.asset_id == asset_id)
    if status_filter:
        query = query.filter(MaintenanceTask.status == status_filter)

    tasks = query.order_by(MaintenanceTask.task_id.desc()).all()
    return [_format_task_response(t, db) for t in tasks]


@router.post("/tasks", response_model=MaintenanceTaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    body: MaintenanceTaskCreate,
    request: Request,
    current_user: User = Depends(require_roles("admin", "manager", "civil_engineer")),
    db: Session = Depends(get_db),
):
    """Create a new maintenance task. Civil engineer, admin, or manager only."""
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == body.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    assignee = None
    if body.assigned_to:
        assignee = db.query(User).filter(User.user_id == body.assigned_to).first()
        if not assignee:
            raise HTTPException(status_code=404, detail="Assigned user not found")

    task = MaintenanceTask(
        asset_id=body.asset_id,
        inspection_id=body.inspection_id,
        priority_id=body.priority_id,
        title=body.title,
        description=body.description,
        task_type=body.task_type,
        priority=body.priority,
        status="assigned" if body.assigned_to else "open",
        assigned_to=body.assigned_to,
        created_by=current_user.user_id,
        due_date=body.due_date,
    )
    db.add(task)
    db.flush()

    publish(
        db=db,
        event_type="task.created",
        entity_type="task",
        entity_id=task.task_id,
        audience={
            "roles": ["admin", "manager", "civil_engineer", "maintenance_engineer"],
            "assigned_to": task.assigned_to,
        },
        payload={
            "task_id": task.task_id,
            "title": task.title,
            "asset_id": task.asset_id,
            "priority": task.priority,
            "assigned_to": task.assigned_to,
        },
    )

    if task.assigned_to:
        publish(
            db=db,
            event_type="task.assigned",
            entity_type="task",
            entity_id=task.task_id,
            audience={
                "user_ids": [task.assigned_to],
                "roles": ["admin", "manager", "civil_engineer"],
            },
            payload={
                "task_id": task.task_id,
                "title": task.title,
                "assigned_to": task.assigned_to,
            },
        )
        create_notification(
            db=db,
            user_id=task.assigned_to,
            type="task_assigned",
            title="New Maintenance Task Assigned",
            body=f"You have been assigned task '{task.title}' for asset '{asset.name}'.",
            entity_type="task",
            entity_id=str(task.task_id),
            severity="medium",
        )

    db.commit()
    db.refresh(task)

    create_audit_log(
        db=db,
        action="create_maintenance_task",
        user_id=current_user.user_id,
        entity_type="maintenance_task",
        entity_id=str(task.task_id),
        ip_address=request.client.host if request.client else None,
    )
    return _format_task_response(task, db)


@router.put("/tasks/{task_id}/status", response_model=MaintenanceTaskResponse)
def update_task_status(
    task_id: int,
    body: MaintenanceTaskStatusUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update status of a maintenance task.
    Maintenance engineers can only update tasks assigned to them.
    """
    task = db.query(MaintenanceTask).filter(MaintenanceTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role == "maintenance_engineer" and task.assigned_to != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only update tasks assigned to you.")

    old_status = task.status
    task.status = body.status
    now = datetime.now(timezone.utc)

    if body.status == "in_progress" and not task.started_at:
        task.started_at = now
    elif body.status == "completed":
        task.completed_at = now
        if body.notes:
            task.resolution_notes = body.notes

        # Notify civil engineers to verify
        publish(
            db=db,
            event_type="task.completed",
            entity_type="task",
            entity_id=task.task_id,
            audience={"roles": ["admin", "manager", "civil_engineer"]},
            payload={
                "task_id": task.task_id,
                "title": task.title,
                "completed_by": current_user.user_id,
            },
        )
        # Notify the task creator or engineers
        if task.created_by:
            create_notification(
                db=db,
                user_id=task.created_by,
                type="task_completed",
                title="Maintenance Task Completed - Verification Required",
                body=f"Task '{task.title}' has been marked completed and requires engineering verification.",
                entity_type="task",
                entity_id=str(task.task_id),
                severity="medium",
            )

    publish(
        db=db,
        event_type="task.status_changed",
        entity_type="task",
        entity_id=task.task_id,
        audience={
            "roles": ["admin", "manager", "civil_engineer", "maintenance_engineer"],
            "assigned_to": task.assigned_to,
        },
        payload={
            "task_id": task.task_id,
            "old_status": old_status,
            "new_status": task.status,
            "assigned_to": task.assigned_to,
        },
    )

    db.commit()
    db.refresh(task)

    create_audit_log(
        db=db,
        action=f"update_task_status_{task.status}",
        user_id=current_user.user_id,
        entity_type="maintenance_task",
        entity_id=str(task.task_id),
        ip_address=request.client.host if request.client else None,
    )
    return _format_task_response(task, db)


@router.put("/tasks/{task_id}/verify", response_model=MaintenanceTaskResponse)
def verify_task(
    task_id: int,
    body: MaintenanceTaskVerifyRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin", "civil_engineer")),
    db: Session = Depends(get_db),
):
    """Civil engineer verifies or reopens completed maintenance task."""
    task = db.query(MaintenanceTask).filter(MaintenanceTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.verified:
        task.status = "verified"
        publish(
            db=db,
            event_type="task.verified",
            entity_type="task",
            entity_id=task.task_id,
            audience={"all": True},
            payload={
                "task_id": task.task_id,
                "verified_by": current_user.user_id,
            },
        )
    else:
        task.status = "in_progress"
        if body.comment:
            task.resolution_notes = f"Reopened by engineer: {body.comment}"

    db.commit()
    db.refresh(task)

    create_audit_log(
        db=db,
        action="verify_maintenance_task" if body.verified else "reopen_maintenance_task",
        user_id=current_user.user_id,
        entity_type="maintenance_task",
        entity_id=str(task.task_id),
        ip_address=request.client.host if request.client else None,
    )
    return _format_task_response(task, db)


@router.post("/priorities/{priority_id}/confirm", response_model=MaintenancePriorityResponse)
def confirm_priority(
    priority_id: int,
    body: MaintenancePriorityConfirmRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin", "civil_engineer")),
    db: Session = Depends(get_db),
):
    """Civil engineer confirms or overrides suggested maintenance priority."""
    priority = db.query(MaintenancePriority).filter(MaintenancePriority.priority_id == priority_id).first()
    if not priority:
        raise HTTPException(status_code=404, detail="Priority record not found")

    priority.final_priority = body.final_priority
    priority.provisional = False
    priority.status = "confirmed"
    priority.reviewed_by = current_user.user_id
    priority.reviewed_at = datetime.now(timezone.utc)
    if body.comment:
        priority.review_comment = body.comment

    publish(
        db=db,
        event_type="priority.confirmed",
        entity_type="maintenance_priority",
        entity_id=priority.priority_id,
        audience={"all": True},
        payload={
            "priority_id": priority.priority_id,
            "asset_id": priority.asset_id,
            "final_priority": priority.final_priority,
            "is_confirmed": True,
        },
    )

    db.commit()
    db.refresh(priority)

    create_audit_log(
        db=db,
        action="confirm_maintenance_priority",
        user_id=current_user.user_id,
        entity_type="maintenance_priority",
        entity_id=str(priority.priority_id),
        ip_address=request.client.host if request.client else None,
    )
    return priority
