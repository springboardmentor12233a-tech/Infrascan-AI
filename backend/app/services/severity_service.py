"""Advisory Damage Severity Assessment Service for InfraScan.

Implements transparent, versioned, engineer-editable rules for advisory damage
severity scoring. Severity is strictly advisory for civil engineer review and
is NOT a structural safety verdict.
"""

import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.services.event_service import publish

logger = logging.getLogger(__name__)

DEFAULT_RULES_PATH = BASE_DIR / "app" / "config" / "severity_rules.json"

SEVERITY_ORDER = ["none", "minor", "moderate", "severe", "critical"]
SEVERITY_RANK = {k: i for i, k in enumerate(SEVERITY_ORDER)}

PRIORITY_ORDER = ["routine_monitoring", "low", "medium", "high", "urgent_engineering_review"]
PRIORITY_RANK = {k: i for i, k in enumerate(PRIORITY_ORDER)}


def load_severity_rules(rules_path: Optional[Union[str, Path]] = None) -> Tuple[Dict[str, Any], str]:
    """Load, validate, and compute SHA-256 for the severity rules JSON.

    Validates:
    - 'rules_version' and 'status' are present.
    - 'bands' cover 0 to 100 with no gaps or overlaps, in ascending order.
    - All factor points and weights are non-negative.

    Returns:
        (rules_dict, sha256_hash)
    Raises:
        ValueError if the file is corrupted or fails validation.
    """
    path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
    if not path.is_file():
        raise ValueError(f"Severity rules file not found: {path}")

    try:
        raw_bytes = path.read_bytes()
        rules_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        rules = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Corrupted severity rules JSON at {path}: {exc}") from exc

    if not isinstance(rules, dict):
        raise ValueError("Severity rules must be a JSON object.")

    if "rules_version" not in rules or not rules["rules_version"]:
        raise ValueError("Missing or empty 'rules_version' in severity rules.")

    if "status" not in rules or not rules["status"]:
        raise ValueError("Missing or empty 'status' in severity rules.")

    # Validate bands covering 0 to 100 with no gaps
    bands = rules.get("bands")
    if not isinstance(bands, list) or len(bands) == 0:
        raise ValueError("Severity rules must include a non-empty 'bands' list.")

    expected_min = 0.0
    for idx, band in enumerate(bands):
        if not isinstance(band, dict):
            raise ValueError(f"Band at index {idx} must be a JSON object.")
        b_min = float(band.get("min_score", -1))
        b_max = float(band.get("max_score", -1))
        severity = band.get("severity")

        if severity not in SEVERITY_RANK:
            raise ValueError(f"Invalid severity '{severity}' in band index {idx}.")

        if b_min > b_max:
            raise ValueError(f"Band index {idx} has min_score ({b_min}) > max_score ({b_max}).")

        if abs(b_min - expected_min) > 1e-4:
            raise ValueError(
                f"Gap or overlap in score bands at index {idx}: expected min {expected_min}, got {b_min}"
            )
        expected_min = b_max

    if abs(expected_min - 100.0) > 1e-4:
        raise ValueError(f"Score bands must end at 100.0, but ended at {expected_min}")

    # Validate factor weights/points are non-negative
    factors_cfg = rules.get("factors", {})
    if not isinstance(factors_cfg, dict):
        raise ValueError("'factors' configuration must be an object.")

    for f_name, f_cfg in factors_cfg.items():
        if not isinstance(f_cfg, dict):
            continue
        # Check thresholds
        thresholds = f_cfg.get("thresholds", [])
        if isinstance(thresholds, list):
            for t in thresholds:
                if isinstance(t, dict) and "points" in t:
                    if float(t["points"]) < 0:
                        raise ValueError(f"Negative points in factor '{f_name}': {t['points']}")
        # Check branching rate thresholds
        rate_th = f_cfg.get("rate_thresholds", [])
        if isinstance(rate_th, list):
            for t in rate_th:
                if isinstance(t, dict) and "points" in t:
                    if float(t["points"]) < 0:
                        raise ValueError(f"Negative rate points in factor '{f_name}': {t['points']}")
        if "multi_component_points" in f_cfg and float(f_cfg["multi_component_points"]) < 0:
            raise ValueError(f"Negative multi_component_points in factor '{f_name}'")
        if "max_points" in f_cfg and float(f_cfg["max_points"]) < 0:
            raise ValueError(f"Negative max_points in factor '{f_name}'")

        # Check damage type weights
        weights = f_cfg.get("weights", {})
        if isinstance(weights, dict):
            for cls_k, pts in weights.items():
                if float(pts) < 0:
                    raise ValueError(f"Negative weight for class '{cls_k}' in factor '{f_name}': {pts}")
        if "default_unknown_points" in f_cfg and float(f_cfg["default_unknown_points"]) < 0:
            raise ValueError(f"Negative default_unknown_points in factor '{f_name}'")

    return rules, rules_sha256


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    """Helper to extract attribute from dict or ORM object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def assess(
    measurement: Optional[Any],
    detections: Optional[List[Any]],
    image_size: Tuple[int, int],
    asset: Optional[Any] = None,
    quality_status: Optional[str] = "good",
    rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Pure advisory damage severity assessment.

    No database access inside this function.
    Returns:
        severity_level: str ("none", "minor", "moderate", "severe", "critical")
        score: float (0.0 to 100.0)
        raw_score: float (sum before cap)
        priority_suggestion: str
        factors: List[Dict[str, Any]] (each with factor, input_value, points, note)
        warnings: List[str]
        rules_version: str
        rules_sha256: str
        needs_review: bool (always True)
        low_confidence_review: bool
    """
    if rules is None:
        rules, rules_sha256 = load_severity_rules()
    else:
        rules_sha256 = hashlib.sha256(json.dumps(rules, sort_keys=True).encode("utf-8")).hexdigest()

    rules_version = rules.get("rules_version", "1.0.0")
    factors_cfg = rules.get("factors", {})

    # Extract image dimensions
    if isinstance(image_size, (tuple, list)) and len(image_size) >= 2:
        img_w, img_h = float(image_size[0]), float(image_size[1])
    elif isinstance(image_size, dict):
        img_w = float(image_size.get("width", 0))
        img_h = float(image_size.get("height", 0))
    else:
        img_w, img_h = 0.0, 0.0

    diag_px = math.sqrt(img_w ** 2 + img_h ** 2) if (img_w > 0 and img_h > 0) else 1.0
    img_area = (img_w * img_h) if (img_w > 0 and img_h > 0) else 1.0

    # Extract crack measurement values
    crack_pixels = int(_get_val(measurement, "crack_pixels", 0) or 0)
    density_percent = float(_get_val(measurement, "density_percent", 0.0) or 0.0)
    length_px = float(_get_val(measurement, "length_px", 0.0) or 0.0)
    avg_width_px = float(_get_val(measurement, "avg_width_px", 0.0) or 0.0)
    max_width_px = float(_get_val(measurement, "max_width_px", 0.0) or 0.0)
    num_components = int(_get_val(measurement, "num_components", 0) or 0)
    num_branch_points = int(_get_val(measurement, "num_branch_points", 0) or 0)
    scale_id = _get_val(measurement, "scale_id", None)
    max_width_mm = _get_val(measurement, "max_width_mm", None)
    width_mm_unc = _get_val(measurement, "width_mm_uncertainty", None)
    mm_per_pixel = _get_val(measurement, "mm_per_pixel", None)

    # Normalize detections list
    raw_detections = detections or []
    norm_detections: List[Dict[str, Any]] = []
    for d in raw_detections:
        norm_detections.append({
            "damage_type": str(_get_val(d, "damage_type", "") or "").strip(),
            "damage_label": str(_get_val(d, "damage_label", "") or "").strip(),
            "confidence": float(_get_val(d, "confidence", 0.0) or 0.0),
            "x_min": float(_get_val(d, "x_min", 0.0) or 0.0),
            "y_min": float(_get_val(d, "y_min", 0.0) or 0.0),
            "x_max": float(_get_val(d, "x_max", 0.0) or 0.0),
            "y_max": float(_get_val(d, "y_max", 0.0) or 0.0),
        })

    yolo_conf = float(factors_cfg.get("damage_type", {}).get("confidence_threshold", 0.25))
    qualifying_detections = [d for d in norm_detections if d["confidence"] >= yolo_conf]

    # Check for empty run
    has_damage = (crack_pixels > 0) or (len(qualifying_detections) > 0)

    factors_list: List[Dict[str, Any]] = []
    warnings: List[str] = []

    # -------------------------------------------------------------
    # Factor a: Crack Density Percent
    # -------------------------------------------------------------
    density_pts = 0.0
    if density_percent < 0.5:
        density_pts = 0.0
    elif density_percent < 2.0:
        density_pts = 10.0
    elif density_percent < 5.0:
        density_pts = 20.0
    elif density_percent < 10.0:
        density_pts = 30.0
    else:
        density_pts = 40.0

    factors_list.append({
        "factor": "crack_density_percent",
        "input_value": round(density_percent, 3),
        "points": density_pts,
        "note": f"Density {density_percent:.2f}% (crack pixels: {crack_pixels})",
    })

    # -------------------------------------------------------------
    # Factor b: Relative Length (length_px / diagonal)
    # -------------------------------------------------------------
    rel_length = (length_px / diag_px) if diag_px > 0 else 0.0
    rel_len_pts = 0.0
    if rel_length < 0.1:
        rel_len_pts = 0.0
    elif rel_length < 0.3:
        rel_len_pts = 5.0
    elif rel_length < 0.6:
        rel_len_pts = 10.0
    elif rel_length < 1.0:
        rel_len_pts = 15.0
    else:
        rel_len_pts = 20.0

    factors_list.append({
        "factor": "relative_length",
        "input_value": round(rel_length, 4),
        "points": rel_len_pts,
        "note": f"Relative length {rel_length:.3f} (length: {length_px:.1f}px, diagonal: {diag_px:.1f}px)",
    })

    # -------------------------------------------------------------
    # Factor c: Branching
    # -------------------------------------------------------------
    branch_rate = ((num_branch_points / length_px) * 1000.0) if length_px > 0 else 0.0
    base_branch_pts = 0.0
    if branch_rate < 2.0:
        base_branch_pts = 0.0
    elif branch_rate < 5.0:
        base_branch_pts = 3.0
    else:
        base_branch_pts = 6.0

    comp_bonus = 2.0 if num_components >= 3 else 0.0
    branch_pts = min(8.0, base_branch_pts + comp_bonus)

    factors_list.append({
        "factor": "branching",
        "input_value": {
            "num_branch_points": num_branch_points,
            "branch_rate_per_1000px": round(branch_rate, 2),
            "num_components": num_components,
        },
        "points": branch_pts,
        "note": (
            f"{num_branch_points} branch points ({branch_rate:.1f}/1000px), "
            f"{num_components} connected components"
        ),
    })

    # -------------------------------------------------------------
    # Factor d: Damage Type Points (maximum over detections >= YOLO_CONF)
    # -------------------------------------------------------------
    weights_dict = factors_cfg.get("damage_type", {}).get("weights", {
        "D00": 10.0, "D10": 10.0, "D20": 25.0, "D40": 30.0,
        "crack": 10.0, "spallation": 30.0, "exposed_bars": 40.0,
        "efflorescence": 10.0, "corrosion_stain": 15.0,
    })
    default_unknown_pts = float(factors_cfg.get("damage_type", {}).get("default_unknown_points", 10.0))

    best_damage_pts = 0.0
    best_damage_type = None
    best_damage_conf = 0.0

    for d in qualifying_detections:
        cls_raw = d["damage_type"] or d["damage_label"]
        cls_key = cls_raw.lower()
        # Find matching key in weights
        matched_pts = None
        for wk, wv in weights_dict.items():
            if wk.lower() == cls_key:
                matched_pts = float(wv)
                break

        if matched_pts is None:
            # Unknown class
            matched_pts = default_unknown_pts
            warn_msg = f"Unknown damage type '{cls_raw}' assigned default score of {default_unknown_pts:.0f} points"
            if warn_msg not in warnings:
                warnings.append(warn_msg)

        if matched_pts > best_damage_pts:
            best_damage_pts = matched_pts
            best_damage_type = cls_raw
            best_damage_conf = d["confidence"]

    factors_list.append({
        "factor": "damage_type",
        "input_value": {
            "best_damage_type": best_damage_type,
            "confidence": round(best_damage_conf, 3),
            "qualifying_count": len(qualifying_detections),
        },
        "points": best_damage_pts,
        "note": (
            f"Highest severity detection: {best_damage_type} (conf {best_damage_conf:.2f})"
            if best_damage_type else "No detections above threshold"
        ),
    })

    # -------------------------------------------------------------
    # Factor e: Damage Area Share (non-crack classes)
    # -------------------------------------------------------------
    non_crack_classes = [c.lower() for c in factors_cfg.get("damage_area_share", {}).get(
        "non_crack_classes", ["d40", "spallation", "exposed_bars", "efflorescence", "corrosion_stain", "pothole"]
    )]
    crack_classes = ["d00", "d10", "d20", "crack"]

    non_crack_box_area = 0.0
    for d in qualifying_detections:
        cls_name = (d["damage_type"] or d["damage_label"]).lower()
        is_non_crack = (cls_name in non_crack_classes) or (cls_name not in crack_classes and not cls_name.startswith("d0") and not cls_name.startswith("d1") and not cls_name.startswith("d2"))
        if is_non_crack:
            box_w = max(0.0, d["x_max"] - d["x_min"])
            box_h = max(0.0, d["y_max"] - d["y_min"])
            non_crack_box_area += (box_w * box_h)

    damage_area_share = (non_crack_box_area / img_area) if img_area > 0 else 0.0
    area_share_pts = 0.0
    if damage_area_share < 0.02:
        area_share_pts = 0.0
    elif damage_area_share < 0.10:
        area_share_pts = 5.0
    elif damage_area_share < 0.25:
        area_share_pts = 10.0
    else:
        area_share_pts = 15.0

    factors_list.append({
        "factor": "damage_area_share",
        "input_value": round(damage_area_share, 4),
        "points": area_share_pts,
        "note": (
            f"Non-crack damage area share {damage_area_share * 100.0:.2f}% "
            f"({non_crack_box_area:.0f}px² / {img_area:.0f}px²)"
        ),
    })

    # -------------------------------------------------------------
    # Factor f: Width mm (ONLY when scale exists)
    # -------------------------------------------------------------
    has_scale = (scale_id is not None or mm_per_pixel is not None) and (max_width_mm is not None)
    width_mm_pts = 0.0
    width_note = ""

    if has_scale and max_width_mm is not None:
        val_w = float(max_width_mm)
        if val_w < 0.3:
            width_mm_pts = 0.0
        elif val_w < 1.0:
            width_mm_pts = 5.0
        elif val_w < 3.0:
            width_mm_pts = 10.0
        elif val_w < 5.0:
            width_mm_pts = 15.0
        else:
            width_mm_pts = 20.0

        unc_str = f" ±{float(width_mm_unc):.2f}mm" if width_mm_unc is not None else ""
        width_note = (
            f"Max width {val_w:.2f}mm{unc_str} (pixel width: {max_width_px:.1f}px). "
            f"Placeholder standard values."
        )
    else:
        width_mm_pts = 0.0
        width_note = f"width not scored: no scale (pixel width: {max_width_px:.1f}px)"

    factors_list.append({
        "factor": "width_mm",
        "input_value": round(float(max_width_mm), 3) if (has_scale and max_width_mm is not None) else None,
        "points": width_mm_pts,
        "note": width_note,
    })

    # -------------------------------------------------------------
    # Total Score and Band Selection
    # -------------------------------------------------------------
    raw_score = sum(f["points"] for f in factors_list)
    score = min(100.0, raw_score)

    if not has_damage:
        score = 0.0
        raw_score = 0.0
        severity_level = "none"
        empty_note = "no damage detected by the AI; this is not evidence that there is no damage"
        if empty_note not in warnings:
            warnings.append(empty_note)
    else:
        # Determine band from score
        if score < 10.0:
            severity_level = "none"
        elif score < 30.0:
            severity_level = "minor"
        elif score < 55.0:
            severity_level = "moderate"
        elif score < 80.0:
            severity_level = "severe"
        else:
            severity_level = "critical"

        # -------------------------------------------------------------
        # Forced Minimums
        # -------------------------------------------------------------
        # 1. exposed_bars with confidence >= 0.5 -> at least severe
        has_exposed_bars = any(
            (d["damage_type"].lower() == "exposed_bars" or d["damage_label"].lower() == "exposed_bars")
            and d["confidence"] >= 0.5
            for d in norm_detections
        )
        if has_exposed_bars:
            if SEVERITY_RANK[severity_level] < SEVERITY_RANK["severe"]:
                severity_level = "severe"
                warnings.append("Forced minimum: severity elevated to severe due to exposed reinforcement bars (conf >= 0.50)")

        # 2. spallation or pothole with damage_area_share >= 0.10 -> at least severe
        has_large_spallation = any(
            (d["damage_type"].lower() in ["spallation", "pothole", "d40"] or d["damage_label"].lower() in ["spallation", "pothole", "d40"])
            for d in qualifying_detections
        ) and (damage_area_share >= 0.10)

        if has_large_spallation:
            if SEVERITY_RANK[severity_level] < SEVERITY_RANK["severe"]:
                severity_level = "severe"
                warnings.append("Forced minimum: severity elevated to severe due to large spallation/pothole (area share >= 10%)")

    # -------------------------------------------------------------
    # Suggested Priority
    # -------------------------------------------------------------
    prio_map = rules.get("priority_mapping", {
        "none": "routine_monitoring",
        "minor": "low",
        "moderate": "medium",
        "severe": "high",
        "critical": "urgent_engineering_review",
    })
    base_priority = prio_map.get(severity_level, "routine_monitoring")

    asset_importance = str(_get_val(asset, "importance_level", "medium") or "medium").lower()
    elevation_map = rules.get("importance_level_elevation", {
        "routine_monitoring": "low",
        "low": "medium",
        "medium": "high",
        "high": "urgent_engineering_review",
        "urgent_engineering_review": "urgent_engineering_review",
    })

    if asset_importance == "high":
        priority_suggestion = elevation_map.get(base_priority, base_priority)
    else:
        priority_suggestion = base_priority

    # -------------------------------------------------------------
    # Review Flags
    # -------------------------------------------------------------
    needs_review = True

    # low_confidence_review when detection confidences used are below 0.4 or quality_status is warning
    low_conf_detections = any(d["confidence"] < 0.40 for d in qualifying_detections)
    low_conf_quality = str(quality_status or "").lower() == "warning"
    low_confidence_review = low_conf_detections or low_conf_quality

    return {
        "severity_level": severity_level,
        "score": round(score, 1),
        "raw_score": round(raw_score, 1),
        "priority_suggestion": priority_suggestion,
        "factors": factors_list,
        "warnings": warnings,
        "rules_version": rules_version,
        "rules_sha256": rules_sha256,
        "needs_review": needs_review,
        "low_confidence_review": low_confidence_review,
    }


def assess_and_save_run(
    run_id: int,
    db: Session,
    rules: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """Execute severity assessment on an AnalysisRun and persist results.

    Updates or inserts SeverityAssessment and updates InspectionSeverity.
    Does not raise exceptions to callers if wrapped; caller logs failures.
    """
    from app.models.analysis import AnalysisRun, CrackMeasurement, Detection
    from app.models.image import Image as ImageModel
    from app.models.severity import SeverityAssessment

    run = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
    if not run:
        logger.warning(f"assess_and_save_run: run_id {run_id} not found.")
        return None

    image = db.query(ImageModel).filter(ImageModel.image_id == run.image_id).first()
    if not image:
        logger.warning(f"assess_and_save_run: image_id {run.image_id} not found.")
        return None

    measurement = db.query(CrackMeasurement).filter(CrackMeasurement.run_id == run.run_id).first()
    detections = db.query(Detection).filter(Detection.run_id == run.run_id).all()

    image_size = (
        getattr(image, "width_px", None) or getattr(image, "width", 0) or 0,
        getattr(image, "height_px", None) or getattr(image, "height", 0) or 0,
    )
    asset = image.inspection.asset if (image.inspection and image.inspection.asset) else None
    quality_status = image.quality_status or "good"

    res = assess(
        measurement=measurement,
        detections=detections,
        image_size=image_size,
        asset=asset,
        quality_status=quality_status,
        rules=rules,
    )

    # Check if an existing assessment exists for this run; mark superseded if recomputing
    existing = (
        db.query(SeverityAssessment)
        .filter(SeverityAssessment.run_id == run.run_id, SeverityAssessment.is_superseded == False)
        .first()
    )

    assessment = SeverityAssessment(
        run_id=run.run_id,
        image_id=image.image_id,
        severity_level=res["severity_level"],
        score=res["score"],
        priority_suggestion=res["priority_suggestion"],
        factors_json=json.dumps(res["factors"]),
        warnings_json=json.dumps(res["warnings"]),
        rules_version=res["rules_version"],
        rules_sha256=res["rules_sha256"],
        review_status="pending",
        is_superseded=False,
    )

    if existing:
        existing.is_superseded = True

    db.add(assessment)
    publish(
        db=db,
        event_type="severity.assessed",
        entity_type="severity_assessment",
        entity_id=assessment.assessment_id or 0,
        audience={"roles": ["admin", "manager", "civil_engineer"]},
        payload={
            "assessment_id": assessment.assessment_id,
            "run_id": run.run_id,
            "image_id": image.image_id,
            "severity_level": assessment.severity_level,
            "is_confirmed": False,
        },
    )
    publish(
        db=db,
        event_type="priority.suggested",
        entity_type="severity_assessment",
        entity_id=assessment.assessment_id or 0,
        audience={"roles": ["admin", "manager", "civil_engineer"]},
        payload={
            "assessment_id": assessment.assessment_id,
            "priority": assessment.priority_suggestion,
            "severity_level": assessment.severity_level,
        },
    )
    db.commit()
    db.refresh(assessment)

    # Update inspection-level severity
    if image.inspection_id:
        update_inspection_severity(image.inspection_id, db)

    return assessment


def update_inspection_severity(inspection_id: int, db: Session) -> Optional[Any]:
    """Aggregate severity assessments for an inspection and persist InspectionSeverity."""
    from app.models.image import Image as ImageModel
    from app.models.severity import InspectionSeverity, SeverityAssessment

    # Find all images for this inspection
    images = db.query(ImageModel).filter(ImageModel.inspection_id == inspection_id).all()
    image_ids = [img.image_id for img in images]

    if not image_ids:
        return None

    # Get active assessments for these images
    assessments = (
        db.query(SeverityAssessment)
        .filter(
            SeverityAssessment.image_id.in_(image_ids),
            SeverityAssessment.is_superseded == False,
        )
        .all()
    )

    # Group by image_id taking the newest assessment
    latest_per_image: Dict[int, SeverityAssessment] = {}
    for a in assessments:
        if a.image_id not in latest_per_image or a.created_at > latest_per_image[a.image_id].created_at:
            latest_per_image[a.image_id] = a

    assessed_list = list(latest_per_image.values())
    images_assessed = len(assessed_list)
    images_pending = sum(1 for a in assessed_list if a.review_status == "pending")

    counts = {level: 0 for level in SEVERITY_ORDER}
    worst_rank = -1
    worst_severity = "none"
    worst_score = 0.0

    for a in assessed_list:
        effective_level = a.final_severity if (a.review_status in ["confirmed", "corrected"] and a.final_severity) else a.severity_level
        effective_level = effective_level if effective_level in SEVERITY_RANK else "none"
        counts[effective_level] = counts.get(effective_level, 0) + 1

        rank = SEVERITY_RANK[effective_level]
        if rank > worst_rank:
            worst_rank = rank
            worst_severity = effective_level
        if a.score > worst_score:
            worst_score = a.score

    summary_data = {
        "counts": counts,
        "worst_severity": worst_severity,
        "worst_score": worst_score,
        "images_assessed": images_assessed,
        "images_pending_review": images_pending,
        "aggregation_rule": "The inspection severity is the WORST image severity (final_severity where reviewed), with counts per level.",
    }

    record = (
        db.query(InspectionSeverity)
        .filter(InspectionSeverity.inspection_id == inspection_id)
        .first()
    )

    if not record:
        record = InspectionSeverity(
            inspection_id=inspection_id,
            worst_severity=worst_severity,
            worst_score=worst_score,
            images_assessed=images_assessed,
            images_pending_review=images_pending,
            summary_json=json.dumps(summary_data),
        )
        db.add(record)
    else:
        record.worst_severity = worst_severity
        record.worst_score = worst_score
        record.images_assessed = images_assessed
        record.images_pending_review = images_pending
        record.summary_json = json.dumps(summary_data)

    db.commit()
    db.refresh(record)
    return record
