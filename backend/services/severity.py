import sys, os
def assess_damage_severity(crack_detected: bool, geometry: dict, defect_count: int, surface_type: str = "Concrete") -> dict:
    """
    Transparent, preliminary damage severity assessment based on the original InfraScan project specification.
    Combines:
    1. Crack detection presence & defect count
    2. Crack density / surface area ratio
    3. Crack width (mean & maximum estimated pixel width)
    4. Crack continuity and branching

    Severity Levels:
    - No Visible Damage (Score: 0 - 15)
    - Minor Damage (Score: 16 - 40)
    - Moderate Damage (Score: 41 - 70)
    - Severe Damage (Score: 71 - 85)
    - Critical / Requires Urgent Engineering Review (Score: 86 - 100)

    NOTE: Visual damage alone is insufficient to determine structural integrity.
    This does NOT constitute a certified structural safety judgment.
    """
    if not crack_detected or geometry.get("crack_area_px", 0) == 0:
        return {
            "severity_level": "No Visible Damage",
            "severity_score": 0.0,
            "severity_reasons": ["No structural cracks or visible surface defects detected in image."],
            "urgent_review_required": False,
            "disclaimer": "Automated preliminary assessment. Not a certified structural safety evaluation."
        }

    reasons = []
    score = 20.0 # Base score for confirmed crack presence

    crack_density = geometry.get("crack_density", 0.0) # percentage
    mean_width = geometry.get("mean_width_px", 0.0)
    max_width = geometry.get("max_width_px", 0.0)
    branches = geometry.get("num_branches", 0)
    components = geometry.get("num_components", 1)

    # 1. Density score addition
    if crack_density < 0.5:
        score += 10.0
        reasons.append(f"Low surface crack density ({crack_density:.2f}% of inspected area).")
    elif crack_density < 2.0:
        score += 25.0
        reasons.append(f"Moderate surface crack density ({crack_density:.2f}% of inspected area).")
    elif crack_density < 5.0:
        score += 40.0
        reasons.append(f"High surface crack density ({crack_density:.2f}% of inspected area).")
    else:
        score += 55.0
        reasons.append(f"Extensive surface crack coverage ({crack_density:.2f}% of inspected area).")

    # 2. Width factor
    if max_width > 20.0 or mean_width > 12.0:
        score += 25.0
        reasons.append(f"Significant crack aperture observed (max estimated width: {max_width:.1f}px).")
    elif max_width > 10.0 or mean_width > 6.0:
        score += 15.0
        reasons.append(f"Noticeable crack aperture observed (max estimated width: {max_width:.1f}px).")
    else:
        score += 5.0
        reasons.append(f"Hairline or narrow crack characteristics (mean width: {mean_width:.1f}px).")

    # 3. Defect count & branching (from actual crack segmentation geometry, NOT COCO objects)
    crack_defect_count = int(geometry.get("num_components", 1))
    if crack_defect_count >= 3 or branches > 10:
        score += 15.0
        reasons.append(f"Multiple crack fracture trajectories ({crack_defect_count} distinct segments) with complex interconnected branching.")
    elif crack_defect_count >= 2 or branches > 4:
        score += 8.0
        reasons.append(f"Multiple discrete crack segments detected ({crack_defect_count} trajectories).")

    score = min(100.0, max(0.0, score))

    if score >= 85.0:
        level = "Critical / Requires Urgent Engineering Review"
        urgent = True
    elif score >= 65.0:
        level = "Severe Damage"
        urgent = True
    elif score >= 40.0:
        level = "Moderate Damage"
        urgent = False
    elif score >= 15.0:
        level = "Minor Damage"
        urgent = False
    else:
        level = "No Visible Damage"
        urgent = False

    return {
        "severity_level": level,
        "severity_score": round(score, 1),
        "severity_reasons": reasons,
        "urgent_review_required": urgent,
        "disclaimer": "Automated preliminary assessment. Not a certified structural safety evaluation."
    }
