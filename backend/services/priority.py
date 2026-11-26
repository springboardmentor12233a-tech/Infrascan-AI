import sys, os
def determine_maintenance_priority(severity: dict, asset_type: str = "Bridge", historical_progression: dict = None) -> dict:
    """
    Transparent, rule-based maintenance prioritization engine according to project specification.
    Combines:
    - Preliminary damage severity level
    - Asset infrastructure criticality (e.g., Bridges/Tunnels carry higher structural risk weight than Pavements)
    - Crack progression rate over time if historical inspections exist
    """
    sev_level = severity.get("severity_level", "No Visible Damage")
    sev_score = severity.get("severity_score", 0.0)

    # Asset criticality multiplier
    type_weight = {
        "bridge": 1.25,
        "dam": 1.30,
        "tunnel": 1.20,
        "building": 1.10,
        "concrete structure": 1.10,
        "wall": 1.0,
        "road": 0.90,
        "pavement": 0.85
    }.get(asset_type.lower(), 1.0)

    priority_score = sev_score * type_weight
    rationale_items = [f"Base damage severity score: {sev_score} ({sev_level})."]

    if type_weight > 1.0:
        rationale_items.append(f"Elevated risk weighting applied for critical asset category ({asset_type}).")
    elif type_weight < 1.0:
        rationale_items.append(f"Standard surface maintenance weighting for {asset_type}.")

    # Historical worsening progression check
    if historical_progression and historical_progression.get("worsening_detected", False):
        priority_score += 15.0
        rationale_items.append(f"Active damage progression detected: crack area expanded by {historical_progression.get('growth_percent', 0):.1f}% since previous inspection.")

    priority_score = min(100.0, priority_score)

    if priority_score >= 80.0 or severity.get("urgent_review_required", False):
        p_level = "Urgent Engineering Review"
        action = "Schedule immediate on-site structural engineer inspection within 24-48 hours. Consider localized load restriction if on bridge deck."
    elif priority_score >= 60.0:
        p_level = "High Priority"
        action = "Schedule maintenance repair within 14 days. Perform ultrasonic or depth evaluation on crack."
    elif priority_score >= 35.0:
        p_level = "Medium Priority"
        action = "Log in scheduled quarterly maintenance cycle. Monitor for crack expansion."
    elif priority_score >= 15.0:
        p_level = "Low Priority"
        action = "Routine visual inspection on next scheduled bi-annual maintenance cycle."
    else:
        p_level = "Routine Monitoring"
        action = "Surface in acceptable condition. Continue normal annual monitoring."

    return {
        "priority_level": p_level,
        "priority_score": round(priority_score, 1),
        "priority_rationale": " ".join(rationale_items),
        "recommended_action": action
    }
