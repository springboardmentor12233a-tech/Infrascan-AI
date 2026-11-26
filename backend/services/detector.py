import os
import cv2
import numpy as np
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Global singleton cached YOLO model instance
_YOLO_MODEL = None
_YOLO_LOAD_ATTEMPTED = False
_YOLO_ERROR_MESSAGE = None

def get_yolo_model():
    """
    Returns the cached YOLO11s model instance.
    Loads models/yolo_best.pt once into memory on first request or startup,
    avoiding expensive model reloading on each inference call.
    """
    global _YOLO_MODEL, _YOLO_LOAD_ATTEMPTED, _YOLO_ERROR_MESSAGE

    if _YOLO_MODEL is not None:
        return _YOLO_MODEL, None

    if _YOLO_LOAD_ATTEMPTED and _YOLO_ERROR_MESSAGE is not None:
        return None, _YOLO_ERROR_MESSAGE

    _YOLO_LOAD_ATTEMPTED = True

    model_dir = os.environ.get(
    "INFRASCAN_MODELS_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models"))
)   
    
    yolo_path = os.path.join(model_dir, "yolo_best.pt")

    if not os.path.exists(yolo_path):
        _YOLO_ERROR_MESSAGE = f"Checkpoint not found at '{yolo_path}'. Ensure yolo_best.pt is in models/."
        logger.warning(_YOLO_ERROR_MESSAGE)
        return None, _YOLO_ERROR_MESSAGE

    try:
        from ultralytics import YOLO
        _YOLO_MODEL = YOLO(yolo_path)
        logger.info(f"YOLO11s checkpoint successfully loaded from {yolo_path}")
        return _YOLO_MODEL, None
    except Exception as exc:
        _YOLO_ERROR_MESSAGE = f"Failed to initialize YOLO model from '{yolo_path}': {str(exc)}"
        logger.error(_YOLO_ERROR_MESSAGE)
        return None, _YOLO_ERROR_MESSAGE


def run_crack_detection(image_bgr: np.ndarray, binary_mask: np.ndarray = None) -> Dict[str, Any]:
    """
    Crack & Surface Damage Detection (Bounding Box Localization).
    Executes real inference using the improved YOLO11s model trained on CRACK500.

    If the checkpoint is loaded:
      - Runs real model inference via Ultralytics predict()
      - Extracts bounding boxes and confidence scores
      - Merges adjacent/overlapping micro-clusters using proximity logic
      - Flags transparently that real model inference was executed

    If checkpoint is missing:
      - Reports explicit warning status rather than silently pretending deep learning ran
      - Uses calibrated computer vision heuristics as fallback
    """
    h, w = image_bgr.shape[:2]
    model, load_err = get_yolo_model()

    if model is not None:
        try:
            # Rigorous Provenance Verification:
            # 1. Check if model explicitly contains custom crack classes
            class_names_lower = [str(n).lower() for n in model.names.values()]
            has_explicit_crack_class = any(
                c in ["crack", "surface_crack", "concrete_crack"]
                for c in class_names_lower
            )
            has_single_class = (len(model.names) == 1)

            # 2. Check for verified provenance metadata file alongside checkpoint
            model_dir = os.environ.get(
                "INFRASCAN_MODELS_DIR",
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "models")
                )
            )
            provenance_file = os.path.join(model_dir, "yolo_provenance.json")

            has_provenance_record = False
            if os.path.exists(provenance_file):
                try:
                    import json
                    with open(provenance_file, "r") as pf:
                        meta = json.load(pf)
                        has_provenance_record = (
                            meta.get("dataset") == "CRACK500"
                            and meta.get("verified") is True
                        )
                except Exception:
                    has_provenance_record = False

            # Require BOTH class structure AND provenance record
            # OR an explicit unique crack class
            is_crack500_model = (
                (has_single_class and has_explicit_crack_class)
                or has_provenance_record
            )

            # Real YOLO11s model inference
            results = model.predict(
                image_bgr,
                imgsz=640,
                conf=0.25,
                iou=0.45,
                verbose=False
            )[0]

            boxes = []
            for b in results.boxes:
                xyxy = b.xyxy[0].cpu().numpy().astype(int).tolist()
                conf = float(b.conf[0].cpu().numpy())
                cls_id = int(b.cls[0].cpu().numpy())

                # Bounding box bounds checking
                x1 = int(max(0, min(w, xyxy[0])))
                y1 = int(max(0, min(h, xyxy[1])))
                x2 = int(max(0, min(w, xyxy[2])))
                y2 = int(max(0, min(h, xyxy[3])))

                # Report genuine class name
                raw_name = model.names.get(cls_id, f"class_{cls_id}")
                label = (
                    "surface_crack"
                    if str(raw_name).lower() in ["crack", "surface_crack"]
                    else raw_name
                )

                boxes.append({
                    "box": [x1, y1, x2, y2],
                    "confidence": round(conf, 4),
                    "label": label,
                    "class_id": cls_id
                })

            # Proximity merging of overlapping / contiguous crack fragments
            merged_boxes = merge_adjacent_boxes(
                boxes, w, h, merge_dist=25
            )

            num_classes = len(model.names)

            if is_crack500_model:
                status_desc = (
                    f"YOLO11s CRACK500 Verified Inference "
                    f"(models/yolo_best.pt, classes={num_classes})"
                )
                valid_detections = merged_boxes
                defect_count = int(len(merged_boxes))
            else:
                # Baseline COCO model is NOT an infrastructure damage detector
                status_desc = (
                    "COCO-Pretrained YOLO11s Baseline "
                    "(models/yolo_best.pt, 80 COCO classes — not crack detector)"
                )
                valid_detections = []
                defect_count = 0

            return {
                "defect_count": defect_count,
                "detections": valid_detections,
                "raw_coco_detections": (
                    merged_boxes if not is_crack500_model else []
                ),
                "model_status": status_desc,
                "is_real_inference": True,
                "is_custom_crack500": is_crack500_model,
                "model_classes": model.names,
                "model_architecture": "YOLO11s (P3-P5)",
                "input_resolution": "640x640"
            }

        except Exception as exc:
            logger.error(f"Error during YOLO11s prediction: {exc}")
            load_err = f"Inference execution error: {str(exc)}"

    # Graceful transparent fallback if checkpoint missing or execution failed
    # Reports genuine status indicating fallback rather than pretending model executed
    if binary_mask is None:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        binary_mask = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            25,
            6
        )


    binary = (binary_mask > 127).astype(np.uint8)

    # 1. Morphological closing to bridge disjoint crack segments
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # 2. Connected Component Analysis
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)

    raw_boxes = []
    min_area = 50
    for i in range(1, num_labels):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area >= min_area:
            x = int(stats[i, cv2.CC_STAT_LEFT])
            y = int(stats[i, cv2.CC_STAT_TOP])
            bw = int(stats[i, cv2.CC_STAT_WIDTH])
            bh = int(stats[i, cv2.CC_STAT_HEIGHT])
            raw_boxes.append([x, y, x + bw, y + bh, area])

    if not raw_boxes:
        return {
            "defect_count": 0,
            "detections": [],
            "model_status": f"Fallback Vision Heuristics (Checkpoint unavailable: {load_err}) - No defect zones found",
            "is_real_inference": False
        }

    # 3. Proximity-Based Box Merging
    merged = True
    boxes = raw_boxes
    merge_dist = 30
    while merged:
        merged = False
        new_boxes = []
        skip_indices = set()

        for i in range(len(boxes)):
            if i in skip_indices:
                continue
            b1 = boxes[i]
            x1_min, y1_min, x1_max, y1_max, a1 = b1

            for j in range(i + 1, len(boxes)):
                if j in skip_indices:
                    continue
                b2 = boxes[j]
                x2_min, y2_min, x2_max, y2_max, a2 = b2

                x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min) + merge_dist)
                y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min) + merge_dist)

                if x_overlap > 0 and y_overlap > 0:
                    x1_min = min(x1_min, x2_min)
                    y1_min = min(y1_min, y2_min)
                    x1_max = max(x1_max, x2_max)
                    y1_max = max(y1_max, y2_max)
                    a1 = a1 + a2
                    skip_indices.add(j)
                    merged = True

            new_boxes.append([x1_min, y1_min, x1_max, y1_max, a1])
        boxes = new_boxes

    detections = []
    pad = 8
    for b in boxes:
        x1, y1, x2, y2, area = b
        conf = min(0.95, round(0.60 + (area / 1800.0), 3))
        detections.append({
            "box": [
                int(max(0, x1 - pad)),
                int(max(0, y1 - pad)),
                int(min(w, x2 + pad)),
                int(min(h, y2 + pad))
            ],
            "confidence": float(conf),
            "label": "surface_crack"
        })

    detections = sorted(detections, key=lambda d: (d["box"][2]-d["box"][0])*(d["box"][3]-d["box"][1]), reverse=True)[:6]

    status_note = f"Fallback Vision Heuristics (Checkpoint notice: {load_err})" if load_err else "Fallback Vision Heuristics"

    return {
        "defect_count": int(len(detections)),
        "detections": detections,
        "model_status": status_note,
        "is_real_inference": False
    }

def merge_adjacent_boxes(boxes: List[Dict[str, Any]], img_w: int, img_h: int, merge_dist: int = 20) -> List[Dict[str, Any]]:
    """Merges adjacent bounding boxes within Euclidean edge proximity threshold."""
    if not boxes or len(boxes) <= 1:
        return boxes
    merged_list = []
    used = set()
    for i in range(len(boxes)):
        if i in used:
            continue
        cur_box = list(boxes[i]["box"])
        cur_conf = float(boxes[i]["confidence"])
        cur_label = boxes[i].get("label", "surface_crack")
        for j in range(i + 1, len(boxes)):
            if j in used:
                continue
            other_box = boxes[j]["box"]
            x_ol = max(0, min(cur_box[2], other_box[2]) - max(cur_box[0], other_box[0]) + merge_dist)
            y_ol = max(0, min(cur_box[3], other_box[3]) - max(cur_box[1], other_box[1]) + merge_dist)
            if x_ol > 0 and y_ol > 0:
                cur_box = [
                    int(min(cur_box[0], other_box[0])),
                    int(min(cur_box[1], other_box[1])),
                    int(max(cur_box[2], other_box[2])),
                    int(max(cur_box[3], other_box[3]))
                ]
                cur_conf = max(cur_conf, float(boxes[j]["confidence"]))
                used.add(j)
        merged_list.append({
            "box": cur_box,
            "confidence": round(cur_conf, 4),
            "label": cur_label
        })
    return merged_list
