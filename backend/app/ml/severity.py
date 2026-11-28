"""Transparent rule-based Damage Severity Assessment."""


def assess_severity(detections: list[dict]) -> dict:
    """
    Assess overall damage severity from verified model detections.
    All automated results require qualified civil engineering review.
    """
    if not detections:
        return {
            "severity": "No Visible Damage",
            "requires_engineering_review": False,
            "disclaimer": "Automated screening found no visible defects. Routine visual verification recommended.",
        }

    max_conf = max(d.get("confidence", 0.0) for d in detections)
    total_cov = sum(d.get("geometry", {}).get("coverage_pct", 0.0) for d in detections)
    count = len(detections)

    if count >= 5 or total_cov >= 15.0 or (max_conf >= 0.85 and total_cov >= 8.0):
        level = "Critical / Requires Urgent Engineering Review"
    elif count >= 3 or total_cov >= 5.0:
        level = "Severe Damage"
    elif count >= 2 or total_cov >= 1.5:
        level = "Moderate Damage"
    else:
        level = "Minor Damage"

    return {
        "severity": level,
        "requires_engineering_review": True,
        "disclaimer": "Automated assessment requires verification by a qualified civil/structural engineer.",
    }

