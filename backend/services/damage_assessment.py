"""
InfraScan Damage Assessment Service (Module 6).

Computes transparent, rule-based civil engineering damage severity categories
based on surface crack density, pixel distributions, and classification confidence.
"""

from typing import Dict

# Civil Engineering Preliminary Visual Assessment Thresholds:
# Surface crack density percentage = (crack_pixels / total_surface_pixels) * 100
SEVERITY_THRESHOLDS = {
    "NONE": 0.0,        # No crack pixels detected (0.0%)
    "LOW": 2.0,         # Slight surface fissures (<= 2.0% coverage)
    "MODERATE": 7.0,    # Noticeable crack networks (2.0% to 7.0% coverage)
    "HIGH": float("inf")# Dense crack formations (> 7.0% coverage)
}


def assess_damage(
    is_cracked: bool,
    crack_pixels: int,
    total_pixels: int,
    crack_percentage: float,
    classification_confidence: float
) -> Dict:
    """
    Evaluates visual crack severity using documented rule-based thresholds.

    Args:
        is_cracked: Boolean flag from classifier (prob >= 0.5).
        crack_pixels: Count of segmented positive crack pixels.
        total_pixels: Total spatial pixels in the evaluated image.
        crack_percentage: Percentage of image area identified as cracks.
        classification_confidence: Probability confidence score from classifier.

    Returns:
        Dict containing severity level, category title, priority, description, advisory notice, and disclaimer.
    """
    if not is_cracked and crack_pixels == 0:
        severity = "None"
        category_title = "No Visible Crack Detected"
        priority = "Low"
        color = "#10b981"  # Emerald green
        description = "No anomalous crack formations or surface defects detected."
        action_recommendation = "Routine scheduled maintenance. No immediate physical inspection required."
    elif crack_percentage <= SEVERITY_THRESHOLDS["LOW"]:
        severity = "Low"
        category_title = "Minor Visible Damage"
        priority = "Low"
        color = "#f59e0b"  # Amber
        description = f"Minor surface hair-cracks detected ({crack_percentage:.2f}% surface area coverage)."
        action_recommendation = (
            "Monitor during scheduled periodic inspections. Check for progressive crack widening or water infiltration."
        )
    elif crack_percentage <= SEVERITY_THRESHOLDS["MODERATE"]:
        severity = "Moderate"
        category_title = "Moderate Visible Damage"
        priority = "High"
        color = "#f97316"  # Orange
        description = f"Distinct surface crack networks detected ({crack_percentage:.2f}% surface area coverage)."
        action_recommendation = (
            "Recommended on-site visual and ultrasonic verification by a qualified civil engineer within 30 days."
        )
    else:
        severity = "High"
        category_title = "Severe Visible Damage - Requires Urgent Engineering Review"
        priority = "Urgent"
        color = "#ef4444"  # Red
        description = f"Extensive surface crack formations detected ({crack_percentage:.2f}% surface area coverage)."
        action_recommendation = (
            "Priority on-site physical evaluation recommended to evaluate structural integrity and load-bearing capacity."
        )

    disclaimer = (
        "Preliminary 2D Computer Vision screening only. Visual pixel assessment does not substitute "
        "for professional in-situ structural engineering diagnostics. Physical crack dimensions (mm) "
        "require on-site calibrated measurement tools."
    )

    return {
        "severity_level": severity,
        "category_title": category_title,
        "suggested_priority": priority,
        "color_code": color,
        "crack_percentage": round(crack_percentage, 2),
        "crack_pixel_count": crack_pixels,
        "total_pixels": total_pixels,
        "description": description,
        "action_recommendation": action_recommendation,
        "disclaimer": disclaimer,
        "thresholds_applied": {
            "none": "0.0%",
            "low": "<= 2.0%",
            "moderate": "2.0% - 7.0%",
            "high": "> 7.0%"
        }
    }
