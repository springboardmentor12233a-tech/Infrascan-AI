from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.asset import InfrastructureAsset
from app.models.inspection import Inspection
from app.models.severity import InspectionSeverity
from app.models.user import User
from app.schemas.inspection import (
    InspectionCreate,
    InspectionResponse,
    InspectionStatusUpdate,
)
from app.services.audit import create_audit_log
from app.services.event_service import publish
from app.services.notification_service import create_notification

router = APIRouter(prefix="/inspections", tags=["Inspections"])


# Helper function to enrich an inspection with names
def format_inspection_response(insp: Inspection) -> InspectionResponse:
    return InspectionResponse(
        inspection_id=insp.inspection_id,
        asset_id=insp.asset_id,
        asset_name=insp.asset.name if insp.asset else None,
        inspector_id=insp.inspector_id,
        inspector_name=insp.inspector.full_name if insp.inspector else None,
        inspection_date=insp.inspection_date,
        status=insp.status,
        created_at=insp.created_at,
    )


# 1. POST /inspections - Create inspection (admin, manager, civil_engineer)
@router.post("", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def create_inspection(
    inspection_data: InspectionCreate,
    request: Request,
    current_user: User = Depends(require_roles("admin", "manager", "civil_engineer")),
    db: Session = Depends(get_db),
):
    """Schedule a new inspection. The assigned user must have the 'inspector' role."""
    # Validate asset exists
    asset = db.query(InfrastructureAsset).filter(
        InfrastructureAsset.asset_id == inspection_data.asset_id
    ).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    # Validate inspector exists and has inspector role
    inspector = db.query(User).filter(User.user_id == inspection_data.inspector_id).first()
    if not inspector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspector user not found")

    if inspector.role != "inspector":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The assigned user must have the 'inspector' role.",
        )

    new_inspection = Inspection(
        asset_id=inspection_data.asset_id,
        inspector_id=inspection_data.inspector_id,
        inspection_date=inspection_data.inspection_date,
        status=inspection_data.status,
    )
    db.add(new_inspection)
    publish(
        db=db,
        event_type="inspection.created",
        entity_type="inspection",
        entity_id=new_inspection.inspection_id,
        audience={
            "roles": ["admin", "manager", "civil_engineer", "inspector"],
            "inspector_id": new_inspection.inspector_id,
        },
        payload={
            "inspection_id": new_inspection.inspection_id,
            "asset_id": new_inspection.asset_id,
            "asset_name": asset.name if asset else None,
            "inspector_id": new_inspection.inspector_id,
            "status": new_inspection.status,
            "inspection_date": new_inspection.inspection_date.isoformat() if new_inspection.inspection_date else None,
        },
    )
    publish(
        db=db,
        event_type="inspection.assigned",
        entity_type="inspection",
        entity_id=new_inspection.inspection_id,
        audience={
            "roles": ["admin", "manager"],
            "user_ids": [new_inspection.inspector_id],
            "inspector_id": new_inspection.inspector_id,
        },
        payload={
            "inspection_id": new_inspection.inspection_id,
            "asset_id": new_inspection.asset_id,
            "inspector_id": new_inspection.inspector_id,
        },
    )
    if new_inspection.inspector_id:
        create_notification(
            db=db,
            user_id=new_inspection.inspector_id,
            type="inspection_assigned",
            title="New Inspection Assigned",
            body=f"You have been assigned to inspection #{new_inspection.inspection_id} for asset '{asset.name}'.",
            entity_type="inspection",
            entity_id=str(new_inspection.inspection_id),
            severity="medium",
        )
    db.commit()
    db.refresh(new_inspection)

    # Record audit log
    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="create_inspection",
        user_id=current_user.user_id,
        entity_type="inspection",
        entity_id=str(new_inspection.inspection_id),
        ip_address=client_ip,
    )

    return format_inspection_response(new_inspection)


# 2. GET /inspections - List inspections with role-based filtering
@router.get("", response_model=List[InspectionResponse])
def list_inspections(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by inspection status"),
    asset_id: Optional[int] = Query(None, description="Filter by asset ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List inspections. Inspectors see only their own; other roles see all."""
    query = db.query(Inspection)

    # Role visibility rule: inspectors only see their assigned inspections
    if current_user.role == "inspector":
        query = query.filter(Inspection.inspector_id == current_user.user_id)

    if status_filter:
        query = query.filter(Inspection.status == status_filter)
    if asset_id:
        query = query.filter(Inspection.asset_id == asset_id)

    inspections = query.order_by(Inspection.inspection_date.desc()).all()
    return [format_inspection_response(i) for i in inspections]


# 3. GET /inspections/{id} - Get single inspection
@router.get("/{id}", response_model=InspectionResponse)
def get_inspection(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve an inspection by ID adhering to role visibility rules."""
    inspection = db.query(Inspection).filter(Inspection.inspection_id == id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    # If user is an inspector, verify they are assigned to this inspection
    if current_user.role == "inspector" and inspection.inspector_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this inspection.",
        )

    return format_inspection_response(inspection)


# 4. PUT /inspections/{id}/status - Update status with role restrictions
@router.put("/{id}/status", response_model=InspectionResponse)
def update_inspection_status(
    id: int,
    status_data: InspectionStatusUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update inspection status.
    - Assigned inspector can set 'in_progress' or 'completed'.
    - Admin, Manager, and Civil Engineer can set any status.
    """
    inspection = db.query(Inspection).filter(Inspection.inspection_id == id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    new_status = status_data.status

    if current_user.role == "inspector":
        # Inspector must be the assigned inspector
        if inspection.inspector_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update inspections assigned to you.",
            )
        # Inspector can only set in_progress or completed
        if new_status not in ["in_progress", "completed"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inspectors can only set status to 'in_progress' or 'completed'.",
            )
    elif current_user.role not in ["admin", "manager", "civil_engineer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update inspection status.",
        )

    inspection.status = new_status
    publish(
        db=db,
        event_type="inspection.status_changed",
        entity_type="inspection",
        entity_id=inspection.inspection_id,
        audience={
            "roles": ["admin", "manager", "civil_engineer", "inspector"],
            "inspector_id": inspection.inspector_id,
        },
        payload={
            "inspection_id": inspection.inspection_id,
            "status": new_status,
            "inspector_id": inspection.inspector_id,
        },
    )
    if new_status == "completed":
        publish(
            db=db,
            event_type="inspection.completed",
            entity_type="inspection",
            entity_id=inspection.inspection_id,
            audience={
                "roles": ["admin", "manager", "civil_engineer"],
            },
            payload={
                "inspection_id": inspection.inspection_id,
                "inspector_id": inspection.inspector_id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        # Notify civil engineers for required engineering review
        insp_sev = db.query(InspectionSeverity).filter(InspectionSeverity.inspection_id == inspection.inspection_id).first()
        worst_level = insp_sev.worst_severity.lower() if insp_sev and insp_sev.worst_severity else "none"
        is_severe = worst_level in ("severe", "critical")

        civil_engineers = db.query(User).filter(User.role == "civil_engineer", User.is_active == True).all()
        for ce in civil_engineers:
            if is_severe:
                notif_title = "Severe Damage Identified"
                notif_body = f"Inspection #{inspection.inspection_id} completed. Severe damage identified - qualified engineering review required. AI result for engineer review, not a final structural safety verdict."
                notif_sev = "critical"
            else:
                notif_title = "Engineering Review Required"
                notif_body = f"Inspection #{inspection.inspection_id} completed and awaits engineering review. AI result for engineer review, not a final structural safety verdict."
                notif_sev = "medium"

            create_notification(
                db=db,
                user_id=ce.user_id,
                type="engineering_review_required",
                title=notif_title,
                body=notif_body,
                entity_type="inspection",
                entity_id=str(inspection.inspection_id),
                severity=notif_sev,
            )
    db.commit()
    db.refresh(inspection)

    # Record audit log
    client_ip = request.client.host if request.client else None
    create_audit_log(
        db=db,
        action="update_inspection_status",
        user_id=current_user.user_id,
        entity_type="inspection",
        entity_id=str(inspection.inspection_id),
        ip_address=client_ip,
    )

    return format_inspection_response(inspection)

