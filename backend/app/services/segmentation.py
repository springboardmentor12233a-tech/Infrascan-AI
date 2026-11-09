"""
app/services/segmentation.py – Crack Segmentation, Detection & Geometry Engine
Milestone 2 Core:
1. Crack pixel segmentation mask generation
2. Bounding box defect localization
3. Crack skeletonization & geometry measurement (length, width, area, density)
4. Crack pattern classification (longitudinal, transverse, diagonal, alligator, hairline)
"""

import io
import json
import logging
from typing import Dict, Any, List, Tuple
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


def segment_crack(image_bytes: bytes, has_crack: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """
    Produces a binary segmentation mask (255=crack, 0=background)
    and an RGBA visual overlay highlighting detected crack boundaries in bright red/crimson.
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
        if area > 40 and (aspect > 1.5 or max(bw, bh) > 24):
            clean_mask[output == i] = 255

    # Connect nearby disjoint fractures
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel_close)

    # Create visual overlay: highlight cracks in vivid Crimson (#ef4444) with transparent alpha blend
    overlay = img_np.copy()
    crack_pixels = clean_mask > 0
    overlay[crack_pixels] = (
        0.35 * overlay[crack_pixels] + 0.65 * np.array([239, 68, 68], dtype=np.float32)
    ).astype(np.uint8)

    # Draw thin border around crack masks
    contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (255, 255, 255), 1)

    return clean_mask, overlay


def extract_crack_geometry_and_boxes(
    mask: np.ndarray,
    img_shape: Tuple[int, int]
) -> Dict[str, Any]:
    """
    Computes crack length, width, area, density, bounding boxes, and morphology classification.
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
            "bounding_boxes": "[]",
            "boxes_list": []
        }

    # Morphological skeletonization to extract crack medial axis
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

    length_px = int(cv2.countNonZero(skel))
    density_pct = round((crack_area_px / (h * w)) * 100.0, 2)

    # Distance transform computes distance from crack pixel to closest edge (half-width)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    max_width_px = round(float(np.max(dist) * 2.0), 1)
    avg_width_px = round(float(crack_area_px / (length_px + 1e-5)), 1)

    # Extract bounding boxes for distinct defect clusters
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    total_dx = 0
    total_dy = 0

    for cnt in contours:
        if cv2.contourArea(cnt) > 25:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            # Add small padding to box
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
                "confidence": 0.91,
                "label": "Crack"
            })
            total_dx += bw
            total_dy += bh

    # Classify crack morphology
    if len(boxes) >= 6 and density_pct > 5.5:
        crack_type = "Alligator / Map Cracking"
    elif total_dy > 1.7 * (total_dx + 1):
        crack_type = "Vertical / Longitudinal Crack"
    elif total_dx > 1.7 * (total_dy + 1):
        crack_type = "Transverse / Horizontal Crack"
    elif max_width_px < 2.5:
        crack_type = "Hairline Crack"
    else:
        crack_type = "Diagonal / Shear Crack"

    return {
        "crack_type": crack_type,
        "crack_length_px": length_px,
        "max_crack_width_px": max_width_px,
        "avg_crack_width_px": avg_width_px,
        "crack_density_pct": density_pct,
        "crack_area_px": crack_area_px,
        "bounding_boxes": json.dumps(boxes),
        "boxes_list": boxes
    }


def draw_bounding_boxes(image_bytes: bytes, boxes_json: str) -> bytes:
    """
    Draws localized bounding boxes with confidence labels onto the image.
    """
    with Image.open(io.BytesIO(image_bytes)) as pil_img:
        pil_img = pil_img.convert("RGB")
        img_np = np.array(pil_img)

    try:
        boxes = json.loads(boxes_json) if boxes_json else []
    except Exception:
        boxes = []

    for b in boxes:
        x1, y1, x2, y2 = b["xmin"], b["ymin"], b["xmax"], b["ymax"]
        conf = b.get("confidence", 0.90)
        label = f"Crack {int(conf * 100)}%"

        # Draw box
        cv2.rectangle(img_np, (x1, y1), (x2, y2), (239, 68, 68), 2)

        # Label background
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
        label_y = max(y1, text_size[1] + 6)
        cv2.rectangle(img_np, (x1, label_y - text_size[1] - 4), (x1 + text_size[0] + 4, label_y + 2), (239, 68, 68), -1)
        cv2.putText(img_np, label, (x1 + 2, label_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

    is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
    if is_success:
        return buffer.tobytes()
    return image_bytes


def render_mask_png(mask: np.ndarray) -> bytes:
    """Encodes a binary mask as PNG."""
    is_success, buffer = cv2.imencode(".png", mask)
    if is_success:
        return buffer.tobytes()
    return b""
