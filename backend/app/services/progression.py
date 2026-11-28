"""
app/services/progression.py – Damage Progression & Historical Analysis Engine
Compares historical inspections of the same asset over time to track crack growth,
new defect formation, and structural deterioration velocity.
"""

from typing import Dict, Any, List, Optional
import json
from sqlalchemy.orm import Session
from app.models.inspection import Inspection, InspectionStatus
from app.models.inspection_image import InspectionImage
from app.models.infrastructure_asset import InfrastructureAsset


def get_asset_progression_timeline(asset_id: int, db: Session) -> Dict[str, Any]:
    """
    Returns chronological timeline of inspections for an asset,
    tracking defect metrics, severity changes, and progression trends.
    """
    asset = db.query(InfrastructureAsset).filter(InfrastructureAsset.id == asset_id).first()
    if not asset:
        return {"error": "Asset not found"}

    inspections = (
        db.query(Inspection)
        .filter(Inspection.asset_id == asset_id)
        .order_by(Inspection.inspection_date.asc())
        .all()
    )

    timeline: List[Dict[str, Any]] = []
    sev_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "None": 0}

    prev_metrics: Optional[Dict[str, Any]] = None

    for insp in inspections:
        images = db.query(InspectionImage).filter(InspectionImage.inspection_id == insp.id).all()
        total_images = len(images)
        cracked_images = [img for img in images if img.has_crack]

        max_sev = "None"
        total_length_px = 0
        total_length_mm = 0.0
        max_width_px = 0.0
        max_width_mm = 0.0
        total_area_px = 0
        avg_density = 0.0
        damage_types_set = set()

        for img in images:
            if img.severity_level and sev_rank.get(img.severity_level, 0) > sev_rank.get(max_sev, 0):
                max_sev = img.severity_level
            total_length_px += img.crack_length_px or 0
            total_length_mm += img.crack_length_mm or 0.0
            total_area_px += img.crack_area_px or 0
            if (img.max_crack_width_px or 0) > max_width_px:
                max_width_px = img.max_crack_width_px
            if (img.max_crack_width_mm or 0) > max_width_mm:
                max_width_mm = img.max_crack_width_mm
            avg_density += img.crack_density_pct or 0.0

            if img.damage_types:
                try:
                    dtypes = json.loads(img.damage_types)
                    for d in dtypes:
                        damage_types_set.add(d.get("damage_type", ""))
                except Exception:
                    pass

        mean_density = round(avg_density / max(1, total_images), 2)

        # Progression delta compared to previous inspection
        progression_status = "Baseline"
        growth_rate_pct = 0.0

        if prev_metrics is not None:
            prev_len = prev_metrics["total_length_px"]
            if prev_len > 0:
                growth_rate_pct = round(((total_length_px - prev_len) / float(prev_len)) * 100.0, 1)

            if total_length_px > prev_len * 1.25 or sev_rank.get(max_sev, 0) > sev_rank.get(prev_metrics["max_severity"], 0):
                progression_status = "Accelerated Deterioration"
            elif total_length_px > prev_len * 1.05:
                progression_status = "Worsening"
            elif total_length_px < prev_len * 0.8:
                progression_status = "Improved (Repaired)"
            else:
                progression_status = "Stable"

        current_entry = {
            "inspection_id": insp.id,
            "inspection_date": insp.inspection_date.isoformat() if insp.inspection_date else None,
            "status": insp.status.value,
            "inspector_name": insp.inspector.full_name if insp.inspector else "Unassigned",
            "total_images": total_images,
            "cracked_images": len(cracked_images),
            "max_severity": max_sev,
            "total_crack_length_px": total_length_px,
            "total_crack_length_mm": round(total_length_mm, 1),
            "max_crack_width_px": max_width_px,
            "max_crack_width_mm": max_width_mm,
            "total_crack_area_px": total_area_px,
            "mean_crack_density_pct": mean_density,
            "detected_damage_categories": sorted(list(damage_types_set)),
            "growth_rate_pct": growth_rate_pct,
            "progression_status": progression_status
        }
        timeline.append(current_entry)
        prev_metrics = current_entry

    return {
        "asset_id": asset.id,
        "asset_code": asset.asset_code,
        "asset_name": asset.name,
        "total_inspections": len(inspections),
        "timeline": timeline
    }


def compare_inspections(
    current_insp_id: int,
    previous_insp_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Directly compares two inspections (e.g. baseline vs current),
    quantifying absolute and percentage growth across crack metrics and defect emergence.
    """
    curr = db.query(Inspection).filter(Inspection.id == current_insp_id).first()
    prev = db.query(Inspection).filter(Inspection.id == previous_insp_id).first()

    if not curr or not prev:
        return {"error": "One or both inspections not found"}

    curr_images = db.query(InspectionImage).filter(InspectionImage.inspection_id == curr.id).all()
    prev_images = db.query(InspectionImage).filter(InspectionImage.inspection_id == prev.id).all()

    def summarize(imgs: List[InspectionImage]):
        tot_len_px = sum(i.crack_length_px or 0 for i in imgs)
        tot_len_mm = sum(i.crack_length_mm or 0.0 for i in imgs)
        max_w_px = max([i.max_crack_width_px or 0.0 for i in imgs], default=0.0)
        max_w_mm = max([i.max_crack_width_mm or 0.0 for i in imgs], default=0.0)
        tot_area_px = sum(i.crack_area_px or 0 for i in imgs)
        cracked = sum(1 for i in imgs if i.has_crack)
        risk = max([i.risk_score or 0.0 for i in imgs], default=0.0)
        dtypes = set()
        for i in imgs:
            if i.damage_types:
                try:
                    for d in json.loads(i.damage_types):
                        dtypes.add(d.get("damage_type", ""))
                except Exception:
                    pass
        return {
            "total_images": len(imgs),
            "cracked_count": cracked,
            "total_length_px": tot_len_px,
            "total_length_mm": round(tot_len_mm, 2),
            "max_width_px": round(max_w_px, 2),
            "max_width_mm": round(max_w_mm, 2),
            "total_area_px": tot_area_px,
            "max_risk_score": round(risk, 1),
            "damage_types": sorted(list(dtypes))
        }

    c_summary = summarize(curr_images)
    p_summary = summarize(prev_images)

    delta_len_px = c_summary["total_length_px"] - p_summary["total_length_px"]
    delta_len_mm = round(c_summary["total_length_mm"] - p_summary["total_length_mm"], 2)
    delta_w_mm = round(c_summary["max_width_mm"] - p_summary["max_width_mm"], 2)
    delta_cracks = c_summary["cracked_count"] - p_summary["cracked_count"]

    new_damage_types = [dt for dt in c_summary["damage_types"] if dt not in p_summary["damage_types"]]

    if delta_len_px > p_summary["total_length_px"] * 0.20 or delta_w_mm > 0.5:
        overall_trend = "Accelerated Deterioration"
        alert_level = "High"
    elif delta_len_px > 0 or delta_w_mm > 0:
        overall_trend = "Active Crack Progression"
        alert_level = "Medium"
    elif delta_len_px < 0:
        overall_trend = "Defect Reduction (Repaired)"
        alert_level = "Informational"
    else:
        overall_trend = "Stable / Quiescent"
        alert_level = "Low"

    return {
        "current_inspection": {
            "id": curr.id,
            "date": curr.inspection_date.isoformat() if curr.inspection_date else None,
            "summary": c_summary
        },
        "previous_inspection": {
            "id": prev.id,
            "date": prev.inspection_date.isoformat() if prev.inspection_date else None,
            "summary": p_summary
        },
        "deltas": {
            "crack_length_px_change": delta_len_px,
            "crack_length_mm_change": delta_len_mm,
            "max_width_mm_change": delta_w_mm,
            "cracked_images_change": delta_cracks,
            "new_defects_identified": new_damage_types,
            "overall_progression_trend": overall_trend,
            "alert_level": alert_level
        }
    }
