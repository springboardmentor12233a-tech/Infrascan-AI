from __future__ import annotations

from typing import Any, Dict


def analyze_damage_progression(
    earlier_finding: Dict[str, Any],
    latest_finding: Dict[str, Any],
    days_elapsed: int = 30,
) -> Dict[str, Any]:
    """
    Compare multi-temporal inspection findings to evaluate crack and damage growth.
    """
    e_len = float(earlier_finding.get("crack_length_px", 0.0) or 0.0)
    l_len = float(latest_finding.get("crack_length_px", 0.0) or 0.0)
    delta_len = round(l_len - e_len, 1)
    len_growth_pct = round((delta_len / e_len * 100.0) if e_len > 0 else 0.0, 1)

    e_w = float(earlier_finding.get("max_width_px", 0.0) or 0.0)
    l_w = float(latest_finding.get("max_width_px", 0.0) or 0.0)
    delta_w = round(l_w - e_w, 2)
    w_growth_pct = round((delta_w / e_w * 100.0) if e_w > 0 else 0.0, 1)

    e_density = float(earlier_finding.get("crack_density_pct", 0.0) or 0.0)
    l_density = float(latest_finding.get("crack_density_pct", 0.0) or 0.0)
    delta_density = round(l_density - e_density, 3)

    e_score = float(earlier_finding.get("severity_score", 0.0) or 0.0)
    l_score = float(latest_finding.get("severity_score", 0.0) or 0.0)
    delta_score = round(l_score - e_score, 1)

    # Determine trend status
    if delta_score <= 0 and delta_len <= 0 and delta_w <= 0:
        trend = "stable"
        summary = "Defect dimensions remain stable with no discernible structural progression."
    elif delta_score < 10.0 and delta_w < 2.0:
        trend = "minor_progression"
        summary = f"Minor growth observed (+{delta_len} px length, +{delta_w} px width) over {days_elapsed} days. Continue monitoring."
    elif delta_score < 25.0:
        trend = "moderate_progression"
        summary = f"Noticeable defect propagation detected (+{len_growth_pct}% length, +{w_growth_pct}% width). Preventive sealing advised."
    else:
        trend = "accelerated_deterioration"
        summary = f"Rapid structural deterioration flagged (+{delta_score} severity points). Immediate civil engineering investigation required."

    return {
        "trend": trend,
        "summary": summary,
        "days_elapsed": days_elapsed,
        "earlier_score": e_score,
        "latest_score": l_score,
        "delta_severity_score": delta_score,
        "delta_length_px": delta_len,
        "length_growth_pct": len_growth_pct,
        "delta_width_px": delta_w,
        "width_growth_pct": w_growth_pct,
        "delta_density_pct": delta_density,
    }
