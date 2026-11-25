import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.comparison import ImageComparison, InspectionComparison
from app.models.inspection import Inspection
from app.models.user import User
from app.schemas.comparison import (
    ImageComparisonResponse,
    InspectionCompareRequest,
    InspectionComparisonResponse,
)
from app.services.audit import create_audit_log
from app.services.event_service import publish

router = APIRouter(tags=["Inspection Comparisons"])


@router.post("/inspections/compare", response_model=InspectionComparisonResponse, status_code=status.HTTP_201_CREATED)
def compare_inspections(
    body: InspectionCompareRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin", "manager", "civil_engineer")),
    db: Session = Depends(get_db),
):
    """Generate pairwise comparison between two inspections of the same asset."""
    prev_insp = db.query(Inspection).filter(Inspection.inspection_id == body.prev_inspection_id).first()
    curr_insp = db.query(Inspection).filter(Inspection.inspection_id == body.curr_inspection_id).first()

    if not prev_insp or not curr_insp:
        raise HTTPException(status_code=404, detail="One or both inspections not found")

    if prev_insp.asset_id != curr_insp.asset_id:
        raise HTTPException(status_code=400, detail="Cannot compare inspections of different assets")

    summary = {
        "prev_inspection_id": prev_insp.inspection_id,
        "curr_inspection_id": curr_insp.inspection_id,
        "asset_id": curr_insp.asset_id,
        "message": "Historical pairwise comparison computed",
    }

    comparison = InspectionComparison(
        asset_id=curr_insp.asset_id,
        prev_inspection_id=prev_insp.inspection_id,
        curr_inspection_id=curr_insp.inspection_id,
        created_by=current_user.user_id,
        summary_json=json.dumps(summary),
    )
    db.add(comparison)
    db.flush()

    publish(
        db=db,
        event_type="comparison.ready",
        entity_type="comparison",
        entity_id=comparison.comparison_id,
        audience={"roles": ["admin", "manager", "civil_engineer"]},
        payload={
            "comparison_id": comparison.comparison_id,
            "asset_id": comparison.asset_id,
            "prev_inspection_id": prev_insp.inspection_id,
            "curr_inspection_id": curr_insp.inspection_id,
        },
    )

    db.commit()
    db.refresh(comparison)

    create_audit_log(
        db=db,
        action="compare_inspections",
        user_id=current_user.user_id,
        entity_type="inspection_comparison",
        entity_id=str(comparison.comparison_id),
        ip_address=request.client.host if request.client else None,
    )
    return comparison


@router.get("/inspections/{inspection_id}/comparisons", response_model=List[InspectionComparisonResponse])
def get_inspection_comparisons(
    inspection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve comparisons associated with an inspection."""
    comps = (
        db.query(InspectionComparison)
        .filter(
            (InspectionComparison.prev_inspection_id == inspection_id)
            | (InspectionComparison.curr_inspection_id == inspection_id)
        )
        .order_by(InspectionComparison.comparison_id.desc())
        .all()
    )
    return comps


@router.get("/comparisons/{comparison_id}", response_model=InspectionComparisonResponse)
def get_comparison_detail(
    comparison_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full details of a comparison."""
    comp = db.query(InspectionComparison).filter(InspectionComparison.comparison_id == comparison_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return comp
