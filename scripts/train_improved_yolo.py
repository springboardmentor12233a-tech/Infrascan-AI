"""
InfraScan — High-Accuracy YOLO Crack Detection Training & Optimization Pipeline
================================================================================
This script addresses the root causes of the low baseline accuracy (mAP50=0.400)
observed during initial Milestone 2 experiments on CRACK500.

Root Causes Identified:
1. Micro-Fragmented Pseudo-Boxes: The raw connected component algorithm derived
   hundreds of tiny disconnected boxes from broken binary masks. Under IoU 0.50,
   a 2-pixel bounding box discrepancy drops IoU below 0.50, causing both false
   negatives and false positives.
2. Model Capacity: YOLO11n (2.6M parameters) at 640x384 downsampled scale loses
   fine crack fracture details.

Four Key Improvements Implemented:
1. Data-Centric Enhancement: Morphological closing (11x11 kernel) + Proximity Box Merging
   (30px threshold) to unify fractured cracks into cohesive structural defect boxes.
2. Architecture Upgrade: Scale from YOLO11n (2.6M params) to YOLO11s (9.4M params).
3. Standard P3-P5 Feature Architecture: Train at imgsz=640 with AdamW optimizer and fine-tuned loss weights.
4. Loss Optimization: Elevated box loss (box=8.5) and distribution focal loss (dfl=2.0).
"""

import os
import cv2
import yaml
import shutil
import numpy as np
from pathlib import Path
from tqdm import tqdm

def reannotate_crack500_masks(images_dir: Path, masks_dir: Path, output_labels_dir: Path, min_area=60, close_ksize=11, merge_dist=30):
    """
    Re-generates YOLO annotations from CRACK500 masks using morphological closing
    and proximity clustering to eliminate fragmented micro-boxes.
    """
    output_labels_dir.mkdir(parents=True, exist_ok=True)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_ksize, close_ksize))

    mask_files = list(masks_dir.rglob("*.png"))
    print(f"Processing {len(mask_files)} masks for improved bounding-box generation...")

    for mask_path in tqdm(mask_files):
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            continue
        h, w = mask.shape[:2]
        binary = (mask > 127).astype(np.uint8)

        # 1. Morphological closing to bridge fractured segments
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # 2. Connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)

        raw_boxes = []
        for i in range(1, num_labels):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area >= min_area:
                x = int(stats[i, cv2.CC_STAT_LEFT])
                y = int(stats[i, cv2.CC_STAT_TOP])
                bw = int(stats[i, cv2.CC_STAT_WIDTH])
                bh = int(stats[i, cv2.CC_STAT_HEIGHT])
                raw_boxes.append([x, y, x + bw, y + bh, area])

        # 3. Proximity merging
        merged = True
        boxes = raw_boxes
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

                    x_ol = max(0, min(x1_max, x2_max) - max(x1_min, x2_min) + merge_dist)
                    y_ol = max(0, min(y1_max, y2_max) - max(y1_min, y2_min) + merge_dist)

                    if x_ol > 0 and y_ol > 0:
                        x1_min = min(x1_min, x2_min)
                        y1_min = min(y1_min, y2_min)
                        x1_max = max(x1_max, x2_max)
                        y1_max = max(y1_max, y2_max)
                        a1 = a1 + a2
                        skip_indices.add(j)
                        merged = True

                new_boxes.append([x1_min, y1_min, x1_max, y1_max, a1])
            boxes = new_boxes

        # 4. Save normalized YOLO format: class_id xc yc bw bh
        label_file = output_labels_dir / f"{mask_path.stem}.txt"
        with open(label_file, "w") as f:
            for b in boxes:
                x1, y1, x2, y2, _ = b
                pad = 6
                x1 = max(0, x1 - pad)
                y1 = max(0, y1 - pad)
                x2 = min(w, x2 + pad)
                y2 = min(h, y2 + pad)

                xc = ((x1 + x2) / 2.0) / w
                yc = ((y1 + y2) / 2.0) / h
                bw = (x2 - x1) / w
                bh = (y2 - y1) / h
                f.write(f"0 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")

    print(f"Re-annotation complete. Output saved to {output_labels_dir}")

def run_training_pipeline(data_yaml_path: str, model_variant="yolo11s.pt", epochs=50, imgsz=640, batch=16):
    """
    Executes training with optimized hyperparameters for thin structural crack detection.
    Recommended environment: GPU-accelerated runtime (NVIDIA T4 / A100 / RTX 3080+).
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Ultralytics not installed. Install via 'pip install ultralytics'.")
        return

    print(f"Initializing {model_variant} with input resolution {imgsz}x{imgsz}...")
    model = YOLO(model_variant)

    results = model.train(
        data=data_yaml_path,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        patience=10,
        save=True,
        plots=True,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        # Crack-specific hyperparameter tuning:
        box=8.5,             # Increased box regression loss weight
        cls=0.5,             # Single-class crack classification weight
        dfl=2.0,             # Distribution Focal Loss weight for boundary alignment
        degrees=15.0,        # Rotation augmentation for arbitrary crack angles
        scale=0.5,           # Scaling augmentation
        fliplr=0.5,          # Horizontal flip
        flipud=0.5,          # Vertical flip
        mosaic=0.5,          # Reduced mosaic to preserve elongated crack continuity
        close_mosaic=10,     # Disable mosaic in last 10 epochs for clean convergence
        device=0 if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"
    )

    print("Training finished. Evaluating on test set...")
    val_results = model.val(split="test", imgsz=imgsz)
    print("Test mAP@50:", val_results.box.map50)
    print("Test mAP@50-95:", val_results.box.map)
    print("Test Precision:", val_results.box.p)
    print("Test Recall:", val_results.box.r)

if __name__ == "__main__":
    print("InfraScan YOLO Accuracy Improvement Module loaded.")
