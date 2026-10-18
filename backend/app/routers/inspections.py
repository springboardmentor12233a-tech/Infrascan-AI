from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.inspection import Inspection, InspectionStatus
from app.models.infrastructure_asset import InfrastructureAsset
from app.models.user import User
from app.schemas.asset_inspection import InspectionCreate, InspectionUpdate, InspectionOut
from app.core.deps import get_current_user, require_roles
from app.services.audit import log_action

router = APIRouter(tags=["Inspections"])


@router.get("/", response_model=List[InspectionOut])
def list_inspections(
    asset_id: Optional[int] = Query(None, description="Filter by asset ID"),
    status: Optional[InspectionStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List inspections. All authenticated users can view.
    Inspectors can also view all or filter by their own.
    """
    query = db.query(Inspection)
    if asset_id:
        query = query.filter(Inspection.asset_id == asset_id)
    if status:
        query = query.filter(Inspection.status == status)

    return query.order_by(Inspection.inspection_date.desc()).all()


@router.get("/{inspection_id}", response_model=InspectionOut)
def get_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found"
        )
    return inspection


@router.post("/", response_model=InspectionOut, status_code=status.HTTP_201_CREATED)
def create_inspection(
    insp_in: InspectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Administrator", "Infrastructure Manager", "Infrastructure Inspector"))
):
    # Verify asset exists
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == insp_in.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset does not exist"
        )

    # Verify inspector user exists
    inspector = db.query(User).filter(User.id == insp_in.inspector_id).first()
    if not inspector:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inspector user does not exist"
        )

    # If role is Infrastructure Inspector, ensure they are creating inspection for themselves
    if current_user.role and current_user.role.name == "Infrastructure Inspector":
        if insp_in.inspector_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inspectors can only create inspections assigned to themselves."
            )

    inspection = Inspection(
        asset_id=insp_in.asset_id,
        inspector_id=insp_in.inspector_id,
        inspection_date=insp_in.inspection_date,
        status=insp_in.status or InspectionStatus.PENDING,
        notes=insp_in.notes
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    log_action(db, action="create", entity="inspection", entity_id=str(inspection.id), user_id=current_user.id)
    return inspection


@router.put("/{inspection_id}", response_model=InspectionOut)
def update_inspection(
    inspection_id: int,
    insp_in: InspectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found"
        )

    role_name = current_user.role.name if current_user.role else ""

    # Permission check:
    # Admin & Manager: update anything
    # Civil Engineer: review (update notes/status)
    # Inspector: update notes/status only if assigned
    if role_name in ["Administrator", "Infrastructure Manager"]:
        pass
    elif role_name == "Civil Engineer":
        # Can review notes and update status
        if insp_in.inspector_id is not None and insp_in.inspector_id != inspection.inspector_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Civil Engineers cannot reassign inspectors."
            )
    elif role_name == "Infrastructure Inspector":
        if inspection.inspector_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own assigned inspections."
            )
        if insp_in.inspector_id is not None and insp_in.inspector_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inspectors cannot reassign inspections."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only access for your role."
        )

    update_data = insp_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(inspection, field, val)

    db.commit()
    db.refresh(inspection)

    log_action(db, action="update", entity="inspection", entity_id=str(inspection.id), user_id=current_user.id)
    return inspection
