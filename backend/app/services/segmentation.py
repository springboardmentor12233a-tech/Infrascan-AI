"""
app/services/segmentation.py – Crack Segmentation, Detection & Geometry Engine
Features:
1. Pixel-level crack mask delineation
2. Medial axis skeletonization & branching junction detection
3. Morphological crack classification into 8 civil engineering categories
4. Physical dimension conversion (px to mm with calibration factor)
5. Multi-defect bounding box localization & overlay rendering
"""

import io
import json
import logging
from typing import Dict, Any, List, Tuple
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)

# Category colors for defect overlays (BGR for OpenCV)
BOX_COLORS = {
    "Crack": (68, 68, 239),                    # Red
    "Concrete Spalling": (22, 115, 249),       # Orange
    "Surface Corrosion": (6, 119, 217),        # Amber
    "Exposed Reinforcement": (247, 85, 168),   # Purple
    "Potholes": (8, 179, 234),                 # Yellow
    "Water Leakage / Staining": (212, 182, 6), # Cyan
    "Delamination": (166, 184, 20),            # Teal
    "Material Erosion": (175, 163, 156),       # Gray
}


def segment_crack(image_bytes: bytes, has_crack: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """
    Produces a binary segmentation mask (255=crack, 0=background)
    and an RGB visual overlay highlighting detected crack boundaries.
    """
    with Image.open(io.BytesIO(image_bytes)) as pil_img:
        pil_img = pil_img.convert("RGB")
        img_np = np.array(pil_img)

    h, w = img_np.shape[:2]

    if not has_crack:
        mask = np.zeros((h, w), dtype=np.uint8)
        overlay = img_np.copy()
        return mask, overlay

    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    cl = clahe.apply(blur)

    # Multi-directional morphological kernels to detect thin crack ridges across all orientations
    k_h = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
    k_v = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 17))
    k_d1 = np.eye(15, dtype=np.uint8)
    k_d2 = np.fliplr(k_d1)

    bh_h = cv2.morphologyEx(cl, cv2.MORPH_BLACKHAT, k_h)
    bh_v = cv2.morphologyEx(cl, cv2.MORPH_BLACKHAT, k_v)
    bh_d1 = cv2.morphologyEx(cl, cv2.MORPH_BLACKHAT, k_d1)
    bh_d2 = cv2.morphologyEx(cl, cv2.MORPH_BLACKHAT, k_d2)

    ridges = np.maximum.reduce([bh_h, bh_v, bh_d1, bh_d2])
    _, binary = cv2.threshold(ridges, 22, 255, cv2.THRESH_BINARY)

    # Filter isolated speckles (aggregate pores) and preserve continuous elongated crack bodies
    nb_components, output, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    clean_mask = np.zeros_like(binary)
    for i in range(1, nb_components):
        area = stats[i, cv2.CC_STAT_AREA]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        aspect = max(bw, bh) / (min(bw, bh) + 1e-4)
        if area > 35 and (aspect > 1.4 or max(bw, bh) > 20):
            clean_mask[output == i] = 255

    # Connect nearby disjoint fractures
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel_close)

    # Create visual overlay: highlight cracks in vivid Crimson (#ef4444)
    overlay = img_np.copy()
    crack_pixels = clean_mask > 0
    overlay[crack_pixels] = (
        0.35 * overlay[crack_pixels] + 0.65 * np.array([239, 68, 68], dtype=np.float32)
    ).astype(np.uint8)

    contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (255, 255, 255), 1)

    return clean_mask, overlay


def compute_skeleton_and_junctions(mask: np.ndarray) -> Tuple[np.ndarray, int]:
    """
    Extracts 1-pixel wide medial axis crack skeleton and counts bifurcation/junction nodes.
    """
    skel = np.zeros_like(mask)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    temp = mask.copy()

    while True:
        eroded = cv2.erode(temp, element)
        opened = cv2.dilate(eroded, element)
        temp2 = cv2.subtract(temp, opened)
        skel = cv2.bitwise_or(skel, temp2)
        temp = eroded.copy()
        if cv2.countNonZero(temp) == 0:
            break

    # Junction detection: count neighbor pixels on 3x3 window around each skeleton point
    skel_norm = (skel > 0).astype(np.uint8)
    kernel_neighbors = np.array([[1, 1, 1], [1, 10, 1], [1, 1, 1]], dtype=np.uint8)
    convolved = cv2.filter2D(skel_norm, -1, kernel_neighbors)
    # A junction pixel has value 10 + at least 3 neighbors (>= 13)
    junctions = np.sum((convolved >= 13) & (skel_norm == 1))

    return skel, int(junctions)


def extract_crack_geometry_and_boxes(
    mask: np.ndarray,
    img_shape: Tuple[int, int],
    calibration_mm_per_px: float = 0.2
) -> Dict[str, Any]:
    """
    Computes crack length, width, area, density, orientation angle, branching junctions,
    bounding boxes, and classifies morphology into standard civil engineering crack categories.
    """
    h, w = img_shape[:2]
    crack_area_px = int(cv2.countNonZero(mask))

    if crack_area_px == 0:
        return {
            "crack_type": "None",
            "crack_length_px": 0,
            "max_crack_width_px": 0.0,
            "avg_crack_width_px": 0.0,
            "crack_density_pct": 0.0,
            "crack_area_px": 0,
            "crack_length_mm": 0.0,
            "max_crack_width_mm": 0.0,
            "avg_crack_width_mm": 0.0,
            "crack_area_mm2": 0.0,
            "orientation_deg": 0.0,
            "branching_points": 0,
            "calibration_mm_per_px": calibration_mm_per_px,
            "bounding_boxes": "[]",
            "boxes_list": []
        }

    skel, junctions = compute_skeleton_and_junctions(mask)
    length_px = int(cv2.countNonZero(skel))
    density_pct = round((crack_area_px / float(h * w)) * 100.0, 2)

    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    max_width_px = round(float(np.max(dist) * 2.0), 1)
    avg_width_px = round(float(crack_area_px / (length_px + 1e-5)), 1)

    # Physical dimension conversions
    length_mm = round(length_px * calibration_mm_per_px, 2)
    max_width_mm = round(max_width_px * calibration_mm_per_px, 2)
    avg_width_mm = round(avg_width_px * calibration_mm_per_px, 2)
    area_mm2 = round(crack_area_px * (calibration_mm_per_px ** 2), 2)

    # Extract bounding boxes and orientation
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    total_dx = 0
    total_dy = 0
    all_points = []

    for cnt in contours:
        if cv2.contourArea(cnt) > 20:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            pad = 4
            x1 = max(0, bx - pad)
            y1 = max(0, by - pad)
            x2 = min(w, bx + bw + pad)
            y2 = min(h, by + bh + pad)
            boxes.append({
                "xmin": int(x1),
                "ymin": int(y1),
                "xmax": int(x2),
                "ymax": int(y2),
                "confidence": 0.92,
                "label": "Crack"
            })
            total_dx += bw
            total_dy += bh
            all_points.append(cnt.reshape(-1, 2))

    # Calculate orientation angle via PCA / minAreaRect
    orientation_deg = 0.0
    if all_points:
        pts = np.vstack(all_points)
        if len(pts) >= 5:
            (_, _), (mw, mh), angle = cv2.minAreaRect(pts)
            if mw < mh:
                angle = (angle + 90.0) % 180.0
            orientation_deg = round(float(angle), 1)

    # Classify crack morphology into 8 standard civil engineering categories:
    if len(boxes) >= 5 and density_pct > 5.0 and junctions >= 4:
        crack_type = "Alligator / Map Cracking"
    elif max_width_px <= 2.0 or max_width_mm <= 0.4:
        crack_type = "Hairline Crack"
    elif total_dy > 2.0 * (total_dx + 1) or (75.0 <= orientation_deg <= 105.0):
        crack_type = "Vertical Crack"
    elif total_dx > 2.0 * (total_dy + 1) or (orientation_deg <= 15.0 or orientation_deg >= 165.0):
        crack_type = "Horizontal Crack"
    elif total_dy > 1.3 * (total_dx + 1):
        crack_type = "Longitudinal Crack"
    elif total_dx > 1.3 * (total_dy + 1):
        crack_type = "Transverse Crack"
    elif 25.0 <= orientation_deg <= 65.0 or 115.0 <= orientation_deg <= 155.0:
        crack_type = "Diagonal Crack"
    else:
        crack_type = "Random / Irregular Crack"

    return {
        "crack_type": crack_type,
        "crack_length_px": length_px,
        "max_crack_width_px": max_width_px,
        "avg_crack_width_px": avg_width_px,
        "crack_density_pct": density_pct,
        "crack_area_px": crack_area_px,
        "crack_length_mm": length_mm,
        "max_crack_width_mm": max_width_mm,
        "avg_crack_width_mm": avg_width_mm,
        "crack_area_mm2": area_mm2,
        "orientation_deg": orientation_deg,
        "branching_points": junctions,
        "calibration_mm_per_px": calibration_mm_per_px,
        "bounding_boxes": json.dumps(boxes),
        "boxes_list": boxes
    }


def draw_bounding_boxes(image_bytes: bytes, boxes_json: str, multi_damage_json: str = None) -> bytes:
    """
    Draws defect bounding boxes with category badges and confidence ratings.
    """
    with Image.open(io.BytesIO(image_bytes)) as pil_img:
        pil_img = pil_img.convert("RGB")
        img_np = np.array(pil_img)

    all_boxes = []
    try:
        if boxes_json:
            parsed = json.loads(boxes_json)
            if isinstance(parsed, list):
                all_boxes.extend(parsed)
    except Exception:
        pass

    try:
        if multi_damage_json:
            parsed_damage = json.loads(multi_damage_json)
            if isinstance(parsed_damage, list):
                for item in parsed_damage:
                    dtype = item.get("damage_type", "Defect")
                    conf = item.get("confidence", 0.85)
                    for b in item.get("boxes", []):
                        all_boxes.append({
                            "xmin": b.get("xmin", 0),
                            "ymin": b.get("ymin", 0),
                            "xmax": b.get("xmax", 0),
                            "ymax": b.get("ymax", 0),
                            "label": dtype,
                            "confidence": conf
                        })
    except Exception:
        pass

    for b in all_boxes:
        x1, y1, x2, y2 = b.get("xmin", 0), b.get("ymin", 0), b.get("xmax", 0), b.get("ymax", 0)
        label_text = b.get("label", "Defect")
        conf = b.get("confidence", 0.90)
        text = f"{label_text} {int(conf * 100)}%"

        color_rgb = BOX_COLORS.get(label_text, (239, 68, 68))

        # Draw box
        cv2.rectangle(img_np, (x1, y1), (x2, y2), color_rgb, 2)

        # Label background
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
        label_y = max(y1, text_size[1] + 6)
        cv2.rectangle(img_np, (x1, label_y - text_size[1] - 4), (x1 + text_size[0] + 4, label_y + 2), color_rgb, -1)
        cv2.putText(img_np, text, (x1 + 2, label_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

    is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
    return buffer.tobytes() if is_success else image_bytes


def render_skeleton_overlay(image_bytes: bytes, mask: np.ndarray) -> bytes:
    """
    Renders 1-pixel crack skeleton and junction nodes overlaid on the original image.
    """
    with Image.open(io.BytesIO(image_bytes)) as pil_img:
        pil_img = pil_img.convert("RGB")
        img_np = np.array(pil_img)

    skel, _ = compute_skeleton_and_junctions(mask)
    overlay = img_np.copy()
    overlay[skel > 0] = [0, 255, 0]  # Green skeleton line

    is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    return buffer.tobytes() if is_success else image_bytes


def render_mask_png(mask: np.ndarray) -> bytes:
    """Encodes a binary mask as PNG."""
    is_success, buffer = cv2.imencode(".png", mask)
    return buffer.tobytes() if is_success else b""
