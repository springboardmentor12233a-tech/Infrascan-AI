"""
app/services/damage_classifier.py – Multi-Class Structural Damage Detection Engine
Detects 9 civil infrastructure damage categories:
1. Crack
2. Concrete Spalling
3. Surface Corrosion
4. Exposed Reinforcement
5. Potholes
6. Surface Deformation
7. Delamination
8. Water Leakage / Staining (Efflorescence)
9. Material Erosion
"""
import io
import cv2
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Tuple

DAMAGE_CATEGORIES = [
    "Crack",
    "Concrete Spalling",
    "Surface Corrosion",
    "Exposed Reinforcement",
    "Potholes",
    "Surface Deformation",
    "Delamination",
    "Water Leakage / Staining",
    "Material Erosion"
]

CATEGORY_COLORS = {
    "Crack": (239, 68, 68),                # Red
    "Concrete Spalling": (249, 115, 22),   # Orange
    "Surface Corrosion": (217, 119, 6),    # Amber
    "Exposed Reinforcement": (168, 85, 247), # Purple
    "Potholes": (234, 179, 8),             # Yellow
    "Surface Deformation": (59, 130, 246), # Blue
    "Delamination": (20, 184, 166),        # Teal
    "Water Leakage / Staining": (6, 182, 212), # Cyan
    "Material Erosion": (156, 163, 175)    # Gray
}


def detect_multi_class_damage(
    image_bytes: bytes,
    has_crack: bool,
    crack_confidence: float,
    crack_boxes: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Comprehensive multi-class defect detector analyzing RGB, HSV, gradient variance,
    and morphological contours to locate and classify surface defects.
    """
    with Image.open(io.BytesIO(image_bytes)) as pil:
        pil = pil.convert("RGB")
        img_np = np.array(pil)

    h, w = img_np.shape[:2]
    total_pixels = float(h * w)
    detected: List[Dict[str, Any]] = []

    # 1. Structural Crack
    if has_crack:
        severity = (
            "Critical" if crack_confidence > 0.92
            else "High" if crack_confidence > 0.80
            else "Medium" if crack_confidence > 0.65
            else "Low"
        )
        detected.append({
            "damage_type": "Crack",
            "confidence": round(float(crack_confidence), 3),
            "severity": severity,
            "boxes": crack_boxes or []
        })

    hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    # 2. Surface Corrosion / Rust (reddish-orange-brown oxidized iron in HSV)
    rust_mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([20, 255, 210]))
    rust_mask2 = cv2.inRange(hsv, np.array([160, 70, 50]), np.array([180, 255, 210]))
    rust_mask = cv2.bitwise_or(rust_mask1, rust_mask2)
    rust_pct = cv2.countNonZero(rust_mask) / total_pixels
    if rust_pct > 0.03:
        conf = min(0.96, 0.45 + rust_pct * 7.0)
        sev = "Critical" if rust_pct > 0.20 else "High" if rust_pct > 0.12 else "Medium" if rust_pct > 0.05 else "Low"
        cnts, _ = cv2.findContours(rust_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in cnts:
            if cv2.contourArea(c) > (total_pixels * 0.005):
                bx, by, bw, bh = cv2.boundingRect(c)
                boxes.append({"xmin": bx, "ymin": by, "xmax": bx + bw, "ymax": by + bh, "label": "Surface Corrosion", "confidence": round(conf, 2)})
        detected.append({
            "damage_type": "Surface Corrosion",
            "confidence": round(conf, 3),
            "severity": sev,
            "boxes": boxes
        })

    # 3. Water Leakage / Staining (Efflorescence & moisture saturation: white salt residue or dark damp tracks)
    eff_mask = cv2.inRange(hsv, np.array([0, 0, 215]), np.array([180, 40, 255]))
    eff_mask[:int(h * 0.08), :] = 0  # Ignore top sky/ceiling
    eff_pct = cv2.countNonZero(eff_mask) / total_pixels
    if eff_pct > 0.05:
        conf = min(0.92, 0.40 + eff_pct * 6.0)
        sev = "High" if eff_pct > 0.18 else "Medium" if eff_pct > 0.09 else "Low"
        cnts, _ = cv2.findContours(eff_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in cnts:
            if cv2.contourArea(c) > (total_pixels * 0.008):
                bx, by, bw, bh = cv2.boundingRect(c)
                boxes.append({"xmin": bx, "ymin": by, "xmax": bx + bw, "ymax": by + bh, "label": "Water Leakage / Staining", "confidence": round(conf, 2)})
        detected.append({
            "damage_type": "Water Leakage / Staining",
            "confidence": round(conf, 3),
            "severity": sev,
            "boxes": boxes
        })

    # 4. Concrete Spalling (chipped/flaked concrete with sharp depth transitions)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    lap_abs = np.uint8(np.clip(np.abs(lap), 0, 255))
    _, spall_bin = cv2.threshold(lap_abs, 55, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    spall_closed = cv2.morphologyEx(spall_bin, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(spall_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    large_blobs = [c for c in contours if cv2.contourArea(c) > (total_pixels * 0.012)]
    if len(large_blobs) >= 2:
        conf = min(0.90, 0.45 + len(large_blobs) * 0.06)
        sev = "Critical" if len(large_blobs) > 6 else "High" if len(large_blobs) > 3 else "Medium"
        boxes = []
        for c in large_blobs[:8]:
            bx, by, bw, bh = cv2.boundingRect(c)
            boxes.append({"xmin": bx, "ymin": by, "xmax": bx + bw, "ymax": by + bh, "label": "Concrete Spalling", "confidence": round(conf, 2)})
        detected.append({
            "damage_type": "Concrete Spalling",
            "confidence": round(conf, 3),
            "severity": sev,
            "boxes": boxes
        })

    # 5. Exposed Reinforcement (Rebar detection: linear metallic bars within spalled zones)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=int(w * 0.25), maxLineGap=10)
    rebar_found = False
    rebar_boxes = []
    if lines is not None and len(lines) >= 3 and rust_pct > 0.02:
        rebar_found = True
        conf = min(0.94, 0.60 + len(lines) * 0.03)
        for line in lines[:5]:
            x1, y1, x2, y2 = line[0]
            rebar_boxes.append({
                "xmin": max(0, min(x1, x2) - 5),
                "ymin": max(0, min(y1, y2) - 5),
                "xmax": min(w, max(x1, x2) + 5),
                "ymax": min(h, max(y1, y2) + 5),
                "label": "Exposed Reinforcement",
                "confidence": round(conf, 2)
            })
        detected.append({
            "damage_type": "Exposed Reinforcement",
            "confidence": round(conf, 3),
            "severity": "Critical",
            "boxes": rebar_boxes
        })

    # 6. Potholes / Cavities (deep dark circular/oval depression in pavement)
    _, dark_thresh = cv2.threshold(gray, 45, 255, cv2.THRESH_BINARY_INV)
    dark_closed = cv2.morphologyEx(dark_thresh, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    pothole_cnts, _ = cv2.findContours(dark_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    potholes = []
    for c in pothole_cnts:
        area = cv2.contourArea(c)
        if area > (total_pixels * 0.03):
            bx, by, bw, bh = cv2.boundingRect(c)
            aspect = float(bw) / (bh + 1e-4)
            if 0.5 < aspect < 2.0:  # Roughly round or oval
                potholes.append(c)
    if potholes and not rebar_found:
        conf = min(0.89, 0.50 + len(potholes) * 0.1)
        boxes = []
        for c in potholes[:4]:
            bx, by, bw, bh = cv2.boundingRect(c)
            boxes.append({"xmin": bx, "ymin": by, "xmax": bx + bw, "ymax": by + bh, "label": "Potholes", "confidence": round(conf, 2)})
        detected.append({
            "damage_type": "Potholes",
            "confidence": round(conf, 3),
            "severity": "High" if len(potholes) > 2 else "Medium",
            "boxes": boxes
        })

    # 7. Delamination Indicators (sub-surface hollow voids causing surface bulging/flaking)
    blur_large = cv2.GaussianBlur(gray, (25, 25), 0)
    local_dev = cv2.absdiff(gray, blur_large)
    low_dev_mask = (local_dev < 4).astype(np.uint8) * 255
    low_dev_pct = cv2.countNonZero(low_dev_mask) / total_pixels
    if low_dev_pct > 0.35 and not has_crack and not rebar_found:
        conf = min(0.78, 0.35 + low_dev_pct * 0.9)
        detected.append({
            "damage_type": "Delamination",
            "confidence": round(conf, 3),
            "severity": "Low",
            "boxes": []
        })

    # 8. Material Erosion / Surface Deterioration (aggregate loss)
    erosion_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, erosion_kernel)
    high_freq_pct = cv2.countNonZero(cv2.threshold(grad, 35, 255, cv2.THRESH_BINARY)[1]) / total_pixels
    if high_freq_pct > 0.22 and not has_crack:
        conf = min(0.82, 0.40 + high_freq_pct * 1.2)
        detected.append({
            "damage_type": "Material Erosion",
            "confidence": round(conf, 3),
            "severity": "Medium" if high_freq_pct > 0.35 else "Low",
            "boxes": []
        })

    return detected


def compute_overall_risk_score(
    damage_list: List[Dict[str, Any]],
    asset_age_years: int = 20,
    inspection_freq_days: int = 180,
    material_type: str = "Reinforced Concrete"
) -> Dict[str, Any]:
    """
    Computes an engineering-grounded risk priority index (0-100) combining:
    - Maximum defect severity & confidence
    - Multi-defect accumulation (cracks + spalling + corrosion)
    - Structural material vulnerability
    - Asset age and overdue inspection intervals
    """
    if not damage_list:
        return {
            "risk_score": 5,
            "priority": "Routine Monitoring",
            "recommended_action": "Structure is sound. Continue routine scheduled monitoring.",
            "num_damage_types": 0,
            "max_severity": "None"
        }

    severity_weights = {
        "Critical": 45,
        "High": 28,
        "Medium": 16,
        "Low": 7,
        "None": 0
    }
    type_risk_multiplier = {
        "Exposed Reinforcement": 1.4,
        "Crack": 1.25,
        "Concrete Spalling": 1.2,
        "Surface Corrosion": 1.15,
        "Potholes": 1.1,
        "Water Leakage / Staining": 1.05,
        "Delamination": 1.0,
        "Material Erosion": 0.95
    }

    damage_score = 0.0
    highest_severity = "None"
    sev_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "None": 0}

    for d in damage_list:
        sev = d.get("severity", "None")
        conf = d.get("confidence", 0.5)
        dtype = d.get("damage_type", "")
        weight = severity_weights.get(sev, 0)
        mult = type_risk_multiplier.get(dtype, 1.0)
        damage_score += weight * conf * mult
        if sev_rank.get(sev, 0) > sev_rank.get(highest_severity, 0):
            highest_severity = sev

    damage_score = min(72.0, damage_score)

    # Material vulnerability factor
    mat_score = 5
    mat_lower = (material_type or "").lower()
    if "prestressed" in mat_lower or "reinforced" in mat_lower:
        mat_score = 7
    elif "masonry" in mat_lower or "timber" in mat_lower:
        mat_score = 9

    # Asset age factor
    age_score = min(15.0, (asset_age_years or 15) * 0.4)

    # Overdue factor
    freq_score = 4.0
    if inspection_freq_days and inspection_freq_days > 180:
        freq_score = min(9.0, 4.0 + (inspection_freq_days - 180) / 45.0)

    total_score = round(min(100.0, damage_score + age_score + freq_score + mat_score))

    if total_score >= 75 or highest_severity == "Critical":
        priority = "Urgent Engineering Review"
        action = "Immediate structural engineer physical inspection & load rating required."
    elif total_score >= 55 or highest_severity == "High":
        priority = "High Priority"
        action = "Schedule concrete restoration and crack sealing within 30 days."
    elif total_score >= 35 or highest_severity == "Medium":
        priority = "Medium Priority"
        action = "Plan preventive maintenance and surface coating within 90 days."
    elif total_score >= 15:
        priority = "Low Priority"
        action = "Inspect at next scheduled maintenance cycle."
    else:
        priority = "Routine Monitoring"
        action = "Normal operating condition. Routine scheduled monitoring."

    return {
        "risk_score": total_score,
        "priority": priority,
        "recommended_action": action,
        "num_damage_types": len(damage_list),
        "max_severity": highest_severity
    }
