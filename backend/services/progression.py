import sys, os
from datetime import datetime

def analyze_historical_progression(db_session, asset_id: int, current_crack_area_px: int) -> dict:
    """
    Historical Damage Progression Analysis:
    Compares the current inspection with past inspections of the same asset.
    Computes crack growth percentage, severity trends, and timeline.
    """
    from models import Inspection, InspectionResult

    if not asset_id:
        return {
            "has_history": False,
            "worsening_detected": False,
            "message": "Standalone inspection not associated with a registered infrastructure asset."
        }

    inspections = (
        db_session.query(Inspection)
        .filter(Inspection.asset_id == asset_id)
        .order_by(Inspection.timestamp.asc())
        .all()
    )

    if len(inspections) <= 1:
        return {
            "has_history": False,
            "inspections_count": len(inspections),
            "worsening_detected": False,
            "message": "Baseline inspection established. Subsequent inspections will track crack progression."
        }

    history_records = []
    for insp in inspections:
        if insp.results:
            history_records.append({
                "inspection_id": insp.id,
                "date": insp.timestamp.strftime("%Y-%m-%d %H:%M"),
                "crack_area_px": insp.results.crack_area_px,
                "mean_width_px": insp.results.mean_width_px,
                "severity_level": insp.results.severity_level,
                "severity_score": insp.results.severity_score
            })

    if len(history_records) >= 2:
        prev_area = history_records[-2]["crack_area_px"]
        if prev_area > 0:
            growth_pct = ((current_crack_area_px - prev_area) / prev_area) * 100.0
        else:
            growth_pct = 100.0 if current_crack_area_px > 0 else 0.0

        worsening = growth_pct > 10.0

        return {
            "has_history": True,
            "inspections_count": len(inspections),
            "worsening_detected": worsening,
            "growth_percent": round(growth_pct, 1),
            "history": history_records,
            "message": f"Historical comparison against previous inspection of same asset: {growth_pct:+.1f}% pixel-area change.",
            "limitations_disclaimer": "Pixel-area difference is an image-space proxy; physical crack expansion cannot be definitively concluded without identical camera distance, optical scale calibration, and orthorectification."
        }

    return {"has_history": False, "worsening_detected": False}
