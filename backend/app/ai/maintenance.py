from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def prioritize_maintenance(
    severity_category: str,
    severity_score: float,
    defect_type: str,
    asset_type: str = "bridge",
    importance_level: str = "medium",
    construction_year: int = 2010,
    progression_trend: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Multi-factor maintenance prioritization & actionable engineering recommendation engine.
    """
    clean_cat = severity_category.lower().strip()
    clean_type = defect_type.lower().strip()
    clean_asset = asset_type.lower().strip()
    clean_imp = importance_level.lower().strip()
    current_year = datetime.now(timezone.utc).year
    age = max(0, current_year - construction_year)

    # Base priority from severity
    if clean_cat == "critical" or severity_score >= 85.0:
        priority = "urgent_engineering_review"
    elif clean_cat == "severe" or severity_score >= 65.0:
        priority = "high"
    elif clean_cat == "moderate" or severity_score >= 35.0:
        priority = "medium"
    elif clean_cat == "minor" or severity_score >= 15.0:
        priority = "low"
    else:
        priority = "routine_monitoring"

    # Escalation rules:
    # High-importance bridges/tunnels with accelerated deterioration get escalated
    if clean_imp == "high" and priority == "high":
        priority = "urgent_engineering_review"
    if clean_asset in ["bridge", "tunnel", "dam"] and clean_cat == "moderate" and age > 30:
        priority = "high"
    if progression_trend == "accelerated_deterioration" and priority in ["low", "medium"]:
        priority = "high"

    # Generate specialized actionable engineering remediation technique
    if "pothole" in clean_type:
        technique = "Cold/Warm Asphalt Patching & Compaction"
        action = "Saw-cut damaged pavement boundary, clear loose aggregate, apply tack coat, and compact hot-mix asphalt."
        cost = "low"
    elif "rebar" in clean_type or "corrosion" in clean_type:
        technique = "Cathodic Protection & Structural Jacketing"
        action = "Expose oxidized rebar, abrasive blast clean rust to SA 2.5, apply zinc-rich epoxy primer, and cast polymer-modified repair mortar."
        cost = "high"
    elif "spalling" in clean_type:
        technique = "Polymer-Modified Concrete Patching"
        action = "Sound test hollow areas with hammer, chisel back to sound concrete, apply bonding slurry, and trowel patch."
        cost = "medium"
    elif "alligator" in clean_type:
        technique = "Full-Depth Pavement Reclamation & Resurfacing"
        action = "Milling of fatigue-failed surface course, structural base reinforcement, and new asphalt overlay."
        cost = "high"
    elif clean_cat in ["critical", "severe"]:
        technique = "Structural Carbon-Fiber (CFRP) Strengthening or Epoxy Grouting"
        action = "Pressure inject structural low-viscosity epoxy resin into crack fissures and install external CFRP composite wraps."
        cost = "high"
    elif clean_cat == "moderate":
        technique = "Pressure Epoxy Injection & Polyurethane Waterproofing"
        action = "Clean crack surface with compressed air, set injection ports, seal surface with polyester putty, and pressure-inject epoxy."
        cost = "medium"
    elif clean_cat == "minor":
        technique = "Elastomeric Acrylic Surface Sealer"
        action = "High-pressure wash surface to eliminate dust and apply penetrating hydrophobic silane-siloxane moisture barrier."
        cost = "low"
    else:
        technique = "Routine Preventive Maintenance"
        action = "Perform routine visual survey and keep drainage channels clear."
        cost = "low"

    urgency_map = {
        "urgent_engineering_review": 3,
        "high": 14,
        "medium": 30,
        "low": 90,
        "routine_monitoring": 180,
    }

    return {
        "priority": priority,
        "action_required": action,
        "recommended_technique": technique,
        "estimated_cost_tier": cost,
        "urgency_days": urgency_map.get(priority, 30),
        "asset_age_years": age,
        "importance_level": clean_imp,
    }
