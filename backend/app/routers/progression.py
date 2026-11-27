from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.damage import DamageAssessment
from app.models.inspection import Inspection
from app.models.user import User
from app.ai.progression import analyze_damage_progression


router = APIRouter(tags=["Damage Progression & Historical Analysis"])


@router.get("/inspections/{inspection_id}/compare/{previous_inspection_id}")
def compare_inspection_progression(
    inspection_id: int,
    previous_inspection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compare current inspection findings against a previous inspection
    to quantify defect growth, crack width propagation, and structural deterioration trend.
    """
    curr_insp = db.query(Inspection).filter(Inspection.inspection_id == inspection_id).first()
    prev_insp = db.query(Inspection).filter(Inspection.inspection_id == previous_inspection_id).first()

    if not curr_insp or not prev_insp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both inspections not found",
        )

    if curr_insp.asset_id != prev_insp.asset_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare inspections of different infrastructure assets",
        )

    # Calculate days elapsed
    curr_date = curr_insp.inspection_date
    prev_date = prev_insp.inspection_date
    days_elapsed = abs((curr_date - prev_date).days) if hasattr(curr_date, "days") or isinstance(curr_date, datetime) else 30

    # Fetch top damage findings from each inspection
    curr_assessments = db.query(DamageAssessment).filter(DamageAssessment.inspection_id == inspection_id).all()
    prev_assessments = db.query(DamageAssessment).filter(DamageAssessment.inspection_id == previous_inspection_id).all()

    curr_top = max(curr_assessments, key=lambda a: a.severity_score) if curr_assessments else None
    prev_top = max(prev_assessments, key=lambda a: a.severity_score) if prev_assessments else None

    earlier_dict = {
        "crack_length_px": getattr(prev_top, "crack_length_px", 0.0),
        "max_width_px": getattr(prev_top, "max_width_px", 0.0),
        "crack_density_pct": getattr(prev_top, "crack_density_pct", 0.0),
        "severity_score": getattr(prev_top, "severity_score", 0.0),
    } if prev_top else {}

    latest_dict = {
        "crack_length_px": getattr(curr_top, "crack_length_px", 0.0),
        "max_width_px": getattr(curr_top, "max_width_px", 0.0),
        "crack_density_pct": getattr(curr_top, "crack_density_pct", 0.0),
        "severity_score": getattr(curr_top, "severity_score", 0.0),
    } if curr_top else {}

    progression = analyze_damage_progression(
        earlier_finding=earlier_dict,
        latest_finding=latest_dict,
        days_elapsed=days_elapsed,
    )

    return {
        "asset_id": curr_insp.asset_id,
        "current_inspection_id": inspection_id,
        "previous_inspection_id": previous_inspection_id,
        "current_date": str(curr_insp.inspection_date),
        "previous_date": str(prev_insp.inspection_date),
        "progression": progression,
    }
