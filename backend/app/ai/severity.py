from __future__ import annotations

from typing import Any, Dict, Optional


DEFECT_WEIGHTS = {
    "no_damage": 0.0,
    "surface_erosion": 15.0,
    "water_staining": 20.0,
    "corrosion": 35.0,
    "longitudinal_crack": 40.0,
    "transverse_crack": 45.0,
    "diagonal_crack": 50.0,
    "concrete_spalling": 65.0,
    "alligator_crack": 75.0,
    "pothole": 80.0,
    "exposed_rebar": 90.0,
}


def assess_damage_severity(
    defect_type: str,
    max_width_px: float,
    length_px: float,
    crack_density_pct: float,
    max_width_mm: Optional[float] = None,
    length_mm: Optional[float] = None,
    importance_level: str = "medium",
) -> Dict[str, Any]:
    """
    Calculate an objective engineering severity rating and numerical score (0-100).
    
    Formula combines:
    - Width factor (weight 0.35)
    - Length/extent factor (weight 0.25)
    - Surface density factor (weight 0.20)
    - Defect type criticality (weight 0.20)
    """
    clean_type = defect_type.lower().strip()
    type_base = DEFECT_WEIGHTS.get(clean_type, 40.0)

    # Use physical millimeters if available, otherwise normalize pixel heuristics
    if max_width_mm is not None:
        # Civil standard: <0.3mm minor, 0.3-1.0mm moderate, 1.0-3.0mm severe, >3.0mm critical
        width_ratio = min(1.0, max_width_mm / 3.0)
    else:
        # Pixel heuristic assuming standard 1024x1024 frame: 5px (~1mm), 15px (~3mm)
        width_ratio = min(1.0, max_width_px / 18.0)

    if length_mm is not None:
        length_ratio = min(1.0, length_mm / 1000.0)  # >1m is critical
    else:
        length_ratio = min(1.0, length_px / 600.0)

    density_ratio = min(1.0, crack_density_pct / 10.0)  # >10% surface coverage is severe

    # Weighted calculation
    score = (
        0.35 * (width_ratio * 100.0) +
        0.25 * (length_ratio * 100.0) +
        0.20 * (density_ratio * 100.0) +
        0.20 * type_base
    )

    # Asset importance modifier (+10% for high-importance bridges/tunnels)
    if importance_level.lower() == "high":
        score = min(100.0, score * 1.10)
    elif importance_level.lower() == "low":
        score = max(0.0, score * 0.90)

    score = round(score, 1)

    # Categorize
    if score < 15.0 and crack_density_pct == 0:
        category = "no_damage"
        action = "Routine inspection on scheduled cycle. Surface intact."
        urgency_days = 180
    elif score < 35.0:
        category = "minor"
        action = "Cosmetic surface distress or hairline cracking. Monitor at next quarterly inspection."
        urgency_days = 90
    elif score < 65.0:
        category = "moderate"
        action = "Progressive cracking or localized surface spall detected. Preventive sealing or crack routing recommended."
        urgency_days = 30
    elif score < 85.0:
        category = "severe"
        action = "Significant structural crack propagation or material loss. Requires formal civil engineering site evaluation and remedial intervention."
        urgency_days = 14
    else:
        category = "critical"
        action = "Critical structural risk. Rebar exposure, severe shear fracture, or pothole hazard. Urgent engineering review and safety shoring/restriction required immediately."
        urgency_days = 3

    return {
        "severity_score": score,
        "severity_category": category,
        "recommended_action": action,
        "urgency_days": urgency_days,
        "defect_type": clean_type,
        "width_factor": round(width_ratio * 100, 1),
        "length_factor": round(length_ratio * 100, 1),
        "density_factor": round(density_ratio * 100, 1),
    }
