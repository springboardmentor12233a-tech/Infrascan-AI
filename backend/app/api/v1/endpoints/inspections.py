from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.models import Inspection, InfrastructureAsset, User
from app.schemas.schemas import InspectionCreate, InspectionOut

router = APIRouter(prefix="/inspections", tags=["Inspections"])


@router.post("", response_model=InspectionOut, status_code=status.HTTP_201_CREATED)
def create_inspection(
    payload: InspectionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Engineer", "Inspector")),
):
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == payload.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referenced infrastructure asset not found")
    if db.query(Inspection).filter(Inspection.inspection_code == payload.inspection_code).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inspection code already exists")
    inspection = Inspection(**payload.model_dump())
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


@router.get("", response_model=list[InspectionOut])
def list_inspections(
    asset_id: str | None = Query(default=None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Inspection)
    if asset_id:
        query = query.filter(Inspection.asset_id == asset_id)
    return query.offset(skip).limit(limit).all()


@router.get("/{inspection_id}", response_model=InspectionOut)
def get_inspection(inspection_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return insp


@router.patch("/{inspection_id}", response_model=InspectionOut)
def update_inspection(
    inspection_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Engineer", "Inspector")),
):
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    allowed_fields = {
        "inspection_status", "weather_conditions", "inspection_notes",
        "environmental_notes", "inspector_id",
    }
    for key, value in payload.items():
        if key in allowed_fields:
            setattr(insp, key, value)
    db.commit()
    db.refresh(insp)
    return insp
