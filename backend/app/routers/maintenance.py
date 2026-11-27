from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.asset import InfrastructureAsset
from app.models.damage import DamageAssessment
from app.models.inspection import Inspection
from app.models.maintenance import (
    ALLOWED_MAINTENANCE_PRIORITIES,
    ALLOWED_MAINTENANCE_STATUSES,
    MaintenanceRecommendation,
)
from app.models.user import User
from app.ai.maintenance import prioritize_maintenance


router = APIRouter(prefix="/maintenance", tags=["Maintenance Prioritization & Remediation"])


class MaintenanceCreateRequest(BaseModel):
    asset_id: int
    inspection_id: Optional[int] = None
    priority: str = "medium"
    action_required: str
    recommended_technique: Optional[str] = None
    estimated_cost_tier: str = "medium"
    urgency_days: int = 30
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class MaintenanceStatusUpdateRequest(BaseModel):
    status: str
    notes: Optional[str] = None


@router.get("/priorities")
def list_maintenance_priorities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve ranked maintenance prioritization schedule across all registered civil assets.
    Ranks findings by priority urgency (urgent_engineering_review > high > medium > low > routine).
    """
    assets = db.query(InfrastructureAsset).all()
    prioritized_list: List[Dict[str, Any]] = []

    for asset in assets:
        # Find latest inspection
        latest_insp = (
            db.query(Inspection)
            .filter(Inspection.asset_id == asset.asset_id)
            .order_by(Inspection.inspection_date.desc())
            .first()
        )
        if not latest_insp:
            continue

        assessments = (
            db.query(DamageAssessment)
            .filter(DamageAssessment.inspection_id == latest_insp.inspection_id)
            .all()
        )
        top_assessment = max(assessments, key=lambda a: a.severity_score) if assessments else None

        sev_cat = getattr(top_assessment, "severity_category", "no_damage")
        sev_score = getattr(top_assessment, "severity_score", 0.0)
        defect_type = getattr(top_assessment, "defect_type", "surface_wear")

        plan = prioritize_maintenance(
            severity_category=sev_cat,
            severity_score=sev_score,
            defect_type=defect_type,
            asset_type=asset.asset_type,
            importance_level=asset.importance_level,
            construction_year=asset.construction_year or 2010,
        )

        prioritized_list.append({
            "asset_id": asset.custom_id or asset.asset_id,
            "raw_asset_id": asset.asset_id,
            "asset_name": asset.name,
            "asset_type": asset.asset_type,
            "material_type": asset.material_type,
            "importance_level": asset.importance_level,
            "latest_inspection_id": latest_insp.inspection_id,
            "latest_inspection_date": str(latest_insp.inspection_date),
            "dominant_defect": defect_type,
            "severity_score": sev_score,
            "severity_category": sev_cat,
            "priority": plan["priority"],
            "action_required": plan["action_required"],
            "recommended_technique": plan["recommended_technique"],
            "estimated_cost_tier": plan["estimated_cost_tier"],
            "urgency_days": plan["urgency_days"],
        })

    # Sort by urgency ranking
    rank_weight = {
        "urgent_engineering_review": 5,
        "high": 4,
        "medium": 3,
        "low": 2,
        "routine_monitoring": 1,
    }
    prioritized_list.sort(key=lambda item: (rank_weight.get(item["priority"], 0), item["severity_score"]), reverse=True)

    return {
        "total_assets_evaluated": len(prioritized_list),
        "items": prioritized_list,
    }


@router.get("/asset/{asset_id}")
def get_asset_maintenance(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve maintenance tasks and recommendation history for a specific asset."""
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    tasks = (
        db.query(MaintenanceRecommendation)
        .filter(MaintenanceRecommendation.asset_id == asset_id)
        .order_by(MaintenanceRecommendation.created_at.desc())
        .all()
    )
    return {
        "asset_id": asset_id,
        "asset_name": asset.name,
        "total_tasks": len(tasks),
        "tasks": [
            {
                "recommendation_id": t.recommendation_id,
                "inspection_id": t.inspection_id,
                "priority": t.priority,
                "action_required": t.action_required,
                "recommended_technique": t.recommended_technique,
                "estimated_cost_tier": t.estimated_cost_tier,
                "urgency_days": t.urgency_days,
                "status": t.status,
                "assigned_to": t.assigned_to,
                "notes": t.notes,
                "created_at": t.created_at,
            }
            for t in tasks
        ],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_maintenance_recommendation(
    payload: MaintenanceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "civil_engineer")),
):
    """Create a new maintenance recommendation work order."""
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.asset_id == payload.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    task = MaintenanceRecommendation(
        asset_id=payload.asset_id,
        inspection_id=payload.inspection_id,
        priority=payload.priority,
        action_required=payload.action_required,
        recommended_technique=payload.recommended_technique,
        estimated_cost_tier=payload.estimated_cost_tier,
        urgency_days=payload.urgency_days,
        assigned_to=payload.assigned_to,
        notes=payload.notes,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "recommendation_id": task.recommendation_id,
        "asset_id": task.asset_id,
        "priority": task.priority,
        "status": task.status,
        "action_required": task.action_required,
        "created_at": task.created_at,
    }


@router.put("/{recommendation_id}/status")
def update_maintenance_status(
    recommendation_id: int,
    payload: MaintenanceStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager", "civil_engineer", "inspector")),
):
    """Update maintenance task progress (pending -> scheduled -> in_progress -> completed)."""
    task = db.query(MaintenanceRecommendation).filter(MaintenanceRecommendation.recommendation_id == recommendation_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance recommendation not found")

    if payload.status not in ALLOWED_MAINTENANCE_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Status must be one of: {ALLOWED_MAINTENANCE_STATUSES}")

    task.status = payload.status
    if payload.notes:
        task.notes = f"{task.notes or ''}\n{payload.notes}".strip()

    db.commit()
    db.refresh(task)
    return {
        "recommendation_id": task.recommendation_id,
        "status": task.status,
        "notes": task.notes,
    }
