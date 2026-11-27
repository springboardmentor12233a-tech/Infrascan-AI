from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import numpy as np

from .geometry import extract_crack_geometry
from .segmentation import generate_crack_mask


def detect_surface_defects(
    image_bgr: np.ndarray,
    binary_mask: Optional[np.ndarray] = None,
    yolo_model: Any = None,
) -> Dict[str, Any]:
    """
    Multi-class surface damage detection identifying defect categories:
    longitudinal_crack, transverse_crack, alligator_crack, diagonal_crack,
    pothole, concrete_spalling, exposed_rebar, corrosion, water_staining.
    """
    h, w = image_bgr.shape[:2]

    # If YOLO model is available and initialized, attempt YOLO inference
    detections: List[Dict[str, Any]] = []
    if yolo_model is not None:
        try:
            results = yolo_model.predict(source=image_bgr, verbose=False, device="cpu")
            if results and len(results) > 0:
                pred = results[0]
                names = pred.names
                boxes = pred.boxes
                if boxes is not None and len(boxes) > 0:
                    for box, conf, cls_id in zip(
                        boxes.xyxy.detach().cpu().numpy(),
                        boxes.conf.detach().cpu().numpy(),
                        boxes.cls.detach().cpu().numpy().astype(int),
                    ):
                        cname = names[cls_id] if isinstance(names, (list, tuple)) else names.get(cls_id, str(cls_id))
                        detections.append({
                            "class_id": int(cls_id),
                            "class_name": str(cname),
                            "confidence": float(conf),
                            "bounding_box": {
                                "x1": float(box[0]),
                                "y1": float(box[1]),
                                "x2": float(box[2]),
                                "y2": float(box[3]),
                            },
                        })
        except Exception:
            pass

    # If binary mask was not supplied, generate one
    if binary_mask is None:
        binary_mask = generate_crack_mask(image_bgr, target_size=(w, h))

    # Extract geometric features
    geom = extract_crack_geometry(binary_mask)
    crack_detected = geom["crack_detected"]
    density = geom["crack_density_pct"]
    angle = geom["orientation_degrees"]
    max_w = geom["max_width_px"]
    length = geom["length_px"]

    # Classify defect type based on morphology and chromatic cues
    primary_defect = "no_damage"
    confidence = 0.95

    if not crack_detected or density < 0.05:
        primary_defect = "no_damage"
        confidence = 0.98
    elif density > 3.5:
        # High branching interconnectivity -> alligator / map cracking
        primary_defect = "alligator_crack"
        confidence = 0.91
    elif max_w > 15.0 and length < max_w * 2.5:
        # Broad circular/oval defect -> pothole or concrete spall
        primary_defect = "pothole" if np.mean(image_bgr) < 80 else "concrete_spalling"
        confidence = 0.88
    else:
        # Directional crack classification based on principal angle
        if 70.0 <= angle <= 110.0:
            primary_defect = "transverse_crack"
            confidence = 0.94
        elif (0.0 <= angle <= 25.0) or (155.0 <= angle <= 180.0):
            primary_defect = "longitudinal_crack"
            confidence = 0.95
        else:
            primary_defect = "diagonal_crack"
            confidence = 0.89

    # If YOLO found a high-confidence detection, blend or use it
    if detections:
        top_yolo = max(detections, key=lambda d: d["confidence"])
        if top_yolo["confidence"] > 0.65:
            primary_defect = top_yolo["class_name"].lower().replace(" ", "_")
            confidence = top_yolo["confidence"]

    # If no YOLO bounding boxes but crack detected, create bounding box from mask contours
    if not detections and crack_detected:
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            bx, by, bw, bh = cv2.boundingRect(c)
            detections.append({
                "class_id": 0,
                "class_name": primary_defect,
                "confidence": confidence,
                "bounding_box": {
                    "x1": float(bx),
                    "y1": float(by),
                    "x2": float(bx + bw),
                    "y2": float(by + bh),
                },
            })

    return {
        "primary_defect": primary_defect,
        "confidence": round(confidence, 3),
        "total_detections": len(detections),
        "detections": detections,
        "geometry": geom,
    }
