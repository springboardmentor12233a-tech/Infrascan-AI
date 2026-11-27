from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.asset import InfrastructureAsset
from app.models.damage import DamageAssessment
from app.models.image import Image as ImageModel
from app.models.inspection import Inspection
from app.models.user import User


router = APIRouter(prefix="/dashboard", tags=["Dashboard & Damage Analytics"])


@router.get("/stats")
def get_dashboard_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve executive dashboard KPIs, defect distributions, severity breakdowns,
    and geographic hotspots for civil engineering management.
    """
    total_assets = db.query(InfrastructureAsset).count()
    total_inspections = db.query(Inspection).count()
    total_images = db.query(ImageModel).count()

    # Severity distribution
    assessments = db.query(DamageAssessment).all()
    severity_breakdown = {
        "critical": 0,
        "severe": 0,
        "moderate": 0,
        "minor": 0,
        "no_damage": 0,
    }
    defect_counts: Dict[str, int] = {}
    critical_findings_count = 0

    for a in assessments:
        cat = a.severity_category.lower() if a.severity_category else "minor"
        if cat in severity_breakdown:
            severity_breakdown[cat] += 1
        if cat in ["critical", "severe"]:
            critical_findings_count += 1

        dtype = a.defect_type.lower() if a.defect_type else "crack"
        defect_counts[dtype] = defect_counts.get(dtype, 0) + 1

    # Damaged assets count (assets having at least one inspection with moderate/severe/critical finding)
    damaged_asset_ids = (
        db.query(Inspection.asset_id)
        .join(DamageAssessment, DamageAssessment.inspection_id == Inspection.inspection_id)
        .filter(DamageAssessment.severity_category.in_(["moderate", "severe", "critical"]))
        .distinct()
        .all()
    )
    damaged_assets_count = len(damaged_asset_ids)

    # Recent inspections
    recent_inspections = (
        db.query(Inspection)
        .order_by(Inspection.inspection_date.desc())
        .limit(6)
        .all()
    )

    # Geographic hotspots: Assets with coordinates and their highest severity
    hotspots: List[Dict[str, Any]] = []
    assets = db.query(InfrastructureAsset).all()
    for asset in assets:
        # Find highest severity assessment for this asset
        top_sev_record = (
            db.query(DamageAssessment)
            .join(Inspection, Inspection.inspection_id == DamageAssessment.inspection_id)
            .filter(Inspection.asset_id == asset.asset_id)
            .order_by(DamageAssessment.severity_score.desc())
            .first()
        )
        if top_sev_record:
            hotspots.append({
                "asset_id": asset.custom_id or asset.asset_id,
                "name": asset.name,
                "asset_type": asset.asset_type,
                "latitude": asset.latitude,
                "longitude": asset.longitude,
                "dominant_defect": top_sev_record.defect_type,
                "severity_category": top_sev_record.severity_category,
                "severity_score": top_sev_record.severity_score,
            })

    return {
        "kpis": {
            "total_assets": total_assets,
            "total_inspections": total_inspections,
            "total_images": total_images,
            "damaged_assets_count": damaged_assets_count,
            "critical_findings_count": critical_findings_count,
            "health_index_pct": round(max(0.0, 100.0 - (damaged_assets_count / total_assets * 100.0)) if total_assets > 0 else 100.0, 1),
        },
        "severity_breakdown": severity_breakdown,
        "defect_distribution": defect_counts,
        "geographic_hotspots": hotspots,
        "recent_inspections": [
            {
                "inspection_id": insp.inspection_id,
                "asset_id": insp.asset_id,
                "asset_name": insp.asset.name if insp.asset else f"Asset #{insp.asset_id}",
                "inspection_date": str(insp.inspection_date),
                "status": insp.status,
            }
            for insp in recent_inspections
        ],
    }
