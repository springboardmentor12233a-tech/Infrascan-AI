"""
app/services/maintenance_priority.py – Maintenance Prioritization Engine
Scores assets based on latest inspection results for maintenance queue ordering.
"""
import json
from datetime import date, datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.infrastructure_asset import InfrastructureAsset
from app.models.inspection import Inspection, InspectionStatus
from app.models.inspection_image import InspectionImage

SEVERITY_SCORE = {"Critical": 100, "High": 75, "Medium": 50, "Low": 25, "None": 0}
DAMAGE_TYPE_BONUS = {"Crack": 20, "Corrosion/Rust": 15, "Spalling": 18, "Efflorescence": 8, "Delamination": 12}

def get_maintenance_queue(db: Session) -> List[Dict[str, Any]]:
    """
    Returns all assets ranked by maintenance priority score (highest first).
    Score is based on: max severity of latest inspection, asset age, overdue status.
    """
    assets = db.query(InfrastructureAsset).all()
    queue = []
    
    for asset in assets:
        # Get latest completed inspection
        latest_inspection = (
            db.query(Inspection)
            .filter(Inspection.asset_id == asset.id, Inspection.status == InspectionStatus.COMPLETED)
            .order_by(Inspection.inspection_date.desc())
            .first()
        )
        
        risk_score = 10  # baseline
        max_severity = "None"
        crack_count = 0
        total_images = 0
        damage_summary = {}
        
        if latest_inspection:
            images = db.query(InspectionImage).filter(InspectionImage.inspection_id == latest_inspection.id).all()
            total_images = len(images)
            
            for img in images:
                if img.severity_level:
                    s = SEVERITY_SCORE.get(img.severity_level, 0)
                    cur = SEVERITY_SCORE.get(max_severity, 0)
                    if s > cur:
                        max_severity = img.severity_level
                
                # Check multi-class damage
                if img.damage_types:
                    try:
                        dtypes = json.loads(img.damage_types)
                        for d in dtypes:
                            dt = d.get("damage_type", "")
                            if dt not in damage_summary:
                                damage_summary[dt] = 0
                            damage_summary[dt] += 1
                    except Exception:
                        pass
                
                if img.has_crack:
                    crack_count += 1
                    risk_score += SEVERITY_SCORE.get(img.severity_level, 0) * 0.4
            
            # Bonus for damage variety
            risk_score += sum(DAMAGE_TYPE_BONUS.get(k, 5) for k in damage_summary.keys())
        
        # Asset age factor
        if asset.construction_year:
            age = date.today().year - asset.construction_year
            risk_score += min(25, age * 0.6)
        
        # Overdue inspection factor
        if asset.inspection_frequency_days and latest_inspection:
            days_since = (date.today() - latest_inspection.inspection_date).days
            if days_since > asset.inspection_frequency_days:
                overdue_days = days_since - asset.inspection_frequency_days
                risk_score += min(20, overdue_days / 10)
        elif not latest_inspection:
            risk_score += 15  # never inspected
        
        risk_score = round(min(100, risk_score))
        
        if risk_score >= 75:
            priority = "Critical"
            action = "Immediate structural intervention required"
        elif risk_score >= 55:
            priority = "High"
            action = "Schedule repair within 30 days"
        elif risk_score >= 35:
            priority = "Medium"
            action = "Plan maintenance within 90 days"
        elif risk_score >= 15:
            priority = "Low"
            action = "Monitor at next scheduled inspection"
        else:
            priority = "Minimal"
            action = "Routine monitoring only"
        
        queue.append({
            "asset_id": asset.id,
            "asset_code": asset.asset_code,
            "asset_name": asset.name,
            "asset_type": asset.type.value if asset.type else "",
            "location": asset.location_text or "",
            "latitude": asset.latitude,
            "longitude": asset.longitude,
            "risk_score": risk_score,
            "priority": priority,
            "recommended_action": action,
            "max_severity": max_severity,
            "crack_count": crack_count,
            "total_images": total_images,
            "damage_types_found": list(damage_summary.keys()),
            "last_inspection_date": latest_inspection.inspection_date.isoformat() if latest_inspection else None,
            "construction_year": asset.construction_year,
        })
    
    # Sort by risk_score descending
    queue.sort(key=lambda x: x["risk_score"], reverse=True)
    return queue
