from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Asset, Inspection, InspectionResult, User
from auth import get_current_user
from routers.inspection import build_inspection_response

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_inspections = db.query(Inspection).count()
    total_assets = db.query(Asset).count()
    cracked_count = db.query(InspectionResult).filter(InspectionResult.crack_detected == True).count()

    # Severity distribution
    severity_counts = {
        "No Visible Damage": 0,
        "Minor Damage": 0,
        "Moderate Damage": 0,
        "Severe Damage": 0,
        "Critical / Requires Urgent Engineering Review": 0
    }
    sev_query = db.query(InspectionResult.severity_level, func.count(InspectionResult.id)).group_by(InspectionResult.severity_level).all()
    for level, count in sev_query:
        if level in severity_counts:
            severity_counts[level] = count

    # Priority distribution
    priority_counts = {
        "Routine Monitoring": 0,
        "Low Priority": 0,
        "Medium Priority": 0,
        "High Priority": 0,
        "Urgent Engineering Review": 0
    }
    prio_query = db.query(InspectionResult.priority_level, func.count(InspectionResult.id)).group_by(InspectionResult.priority_level).all()
    for level, count in prio_query:
        if level in priority_counts:
            priority_counts[level] = count

    # Defect categories
    defect_categories = {
        "Surface Cracks": cracked_count,
        "Spalling / Deep Aperture": db.query(InspectionResult).filter(InspectionResult.max_width_px > 15).count(),
        "Interconnected / Map Cracking": db.query(InspectionResult).filter(InspectionResult.num_branches > 6).count(),
        "Linear / Hairline": db.query(InspectionResult).filter(InspectionResult.crack_detected == True, InspectionResult.mean_width_px <= 6).count()
    }

    recent_inspections = db.query(Inspection).order_by(Inspection.timestamp.desc()).limit(6).all()

    return {
        "total_inspections": total_inspections,
        "total_assets": total_assets,
        "cracked_count": cracked_count,
        "severity_distribution": severity_counts,
        "priority_distribution": priority_counts,
        "defect_categories": defect_categories,
        "recent_inspections": [build_inspection_response(i) for i in recent_inspections]
    }

@router.get("/user-stats")
def get_user_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns metrics and recent inspections specific to the authenticated registered user."""
    user_inspections_query = db.query(Inspection).filter(Inspection.user_id == current_user.id)
    total_inspections = user_inspections_query.count()

    cracked_count = db.query(InspectionResult).join(Inspection).filter(
        Inspection.user_id == current_user.id,
        InspectionResult.crack_detected == True
    ).count()

    critical_count = db.query(InspectionResult).join(Inspection).filter(
        Inspection.user_id == current_user.id,
        (InspectionResult.severity_level.like("%Critical%")) | (InspectionResult.urgent_review_required == True)
    ).count()

    recent_raw = user_inspections_query.order_by(Inspection.timestamp.desc()).limit(5).all()
    recent = [build_inspection_response(i) for i in recent_raw]

    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "last_login": current_user.last_login
        },
        "stats": {
            "total_inspections": total_inspections,
            "cracked_count": cracked_count,
            "critical_count": critical_count,
            "sound_count": max(0, total_inspections - cracked_count)
        },
        "recent_inspections": recent
    }
