from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Asset, Inspection, InspectionResult

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/summary")
def get_analytics_summary(db: Session = Depends(get_db)):
    results = db.query(InspectionResult).all()
    if not results:
        return {
            "total_evaluated": 0,
            "mean_crack_area_px": 0,
            "mean_skeleton_length_px": 0,
            "mean_crack_width_px": 0,
            "critical_defects_count": 0,
            "urgent_review_count": 0
        }

    cracked = [r for r in results if r.crack_detected]
    return {
        "total_evaluated": len(results),
        "cracked_samples": len(cracked),
        "mean_crack_area_px": round(sum(r.crack_area_px for r in cracked) / max(len(cracked), 1), 1),
        "mean_skeleton_length_px": round(sum(r.skeleton_length_px for r in cracked) / max(len(cracked), 1), 1),
        "mean_crack_width_px": round(sum(r.mean_width_px for r in cracked) / max(len(cracked), 1), 2),
        "critical_defects_count": sum(1 for r in results if "Critical" in r.severity_level),
        "urgent_review_count": sum(1 for r in results if r.urgent_review_required)
    }

@router.get("/historical/{asset_id}")
def get_asset_history(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        return {"error": "Asset not found"}
    
    inspections = db.query(Inspection).filter(Inspection.asset_id == asset_id).order_by(Inspection.timestamp.asc()).all()
    timeline = []
    for insp in inspections:
        res = insp.results
        if res:
            timeline.append({
                "inspection_id": insp.id,
                "timestamp": insp.timestamp.strftime("%Y-%m-%d %H:%M"),
                "severity_level": res.severity_level,
                "severity_score": res.severity_score,
                "crack_area_px": res.crack_area_px,
                "mean_width_px": res.mean_width_px,
                "priority_level": res.priority_level
            })

    return {
        "asset_id": asset.id,
        "asset_name": asset.name,
        "asset_type": asset.type,
        "inspections_count": len(inspections),
        "timeline": timeline
    }
