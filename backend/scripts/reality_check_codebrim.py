"""Local reality check script for trained CODEBRIM defect detector.

Evaluates the trained RT-DETR-L model on 5 real test images from
data/processed/codebrim_yolo/images/test/ on CPU, verifies detections,
prints inference speed and detections, and saves annotated debug images to
backend/storage/debug_codebrim/.
"""

import sys
import time
from pathlib import Path
import cv2
import numpy as np
import torch

# Base project paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
INFRASCAN_DIR = BACKEND_DIR.parent
WORKSPACE_ROOT = INFRASCAN_DIR.parent

# Set paths
WEIGHTS_PATH = INFRASCAN_DIR / "ml" / "models" / "detection_codebrim" / "A2_rtdetr_l" / "weights" / "best.pt"
TEST_IMG_DIR = WORKSPACE_ROOT / "data" / "processed" / "codebrim_yolo" / "images" / "test"
TEST_LBL_DIR = WORKSPACE_ROOT / "data" / "processed" / "codebrim_yolo" / "labels" / "test"
OUTPUT_DIR = BACKEND_DIR / "storage" / "debug_codebrim"

CLASS_NAMES = {
    0: "crack",
    1: "spallation",
    2: "exposed_bars",
    3: "efflorescence",
    4: "corrosion_stain",
}

CLASS_COLORS = {
    0: (16, 185, 129),   # crack (emerald/green)
    1: (249, 115, 22),   # spallation (orange)
    2: (220, 38, 38),    # exposed_bars (red)
    3: (6, 182, 212),    # efflorescence (cyan)
    4: (168, 85, 247),   # corrosion_stain (purple)
}


def main():
    print("=" * 70)
    print("CODEBRIM LOCAL REALITY CHECK (CPU INFERENCE)")
    print("=" * 70)

    if not WEIGHTS_PATH.exists():
        print(f"ERROR: Model weights not found at: {WEIGHTS_PATH}")
        sys.exit(1)

    print(f"Weights file: {WEIGHTS_PATH} ({WEIGHTS_PATH.stat().st_size / (1024*1024):.2f} MB)")
    print(f"Using device: CPU (torch.get_num_threads={torch.get_num_threads()})")

    # Load model
    print("\nLoading RT-DETR model...")
    t0 = time.time()
    from ultralytics import RTDETR
    model = RTDETR(str(WEIGHTS_PATH))
    load_time = time.time() - t0
    print(f"Model loaded successfully in {load_time:.2f}s")
    print(f"Model names map: {model.names}")

    # Ensure output dir exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 5 selected test images covering varied defect classes
    sample_files = [
        "image_0000050.jpg",
        "image_0000126.jpg",
        "image_0000131.jpg",
        "image_0000150.jpg",
        "image_0000235.jpg",
    ]

    total_detections = 0
    total_time = 0.0

    print("\n" + "-" * 70)
    print(f"Running inference on {len(sample_files)} test images at imgsz=960, conf=0.563:")
    print("-" * 70)

    for img_name in sample_files:
        img_path = TEST_IMG_DIR / img_name
        lbl_path = TEST_LBL_DIR / f"{Path(img_name).stem}.txt"

        if not img_path.exists():
            print(f"Warning: Image {img_name} not found at {img_path}")
            continue

        orig_bgr = cv2.imread(str(img_path))
        if orig_bgr is None:
            print(f"Warning: Failed to decode {img_name}")
            continue

        h, w = orig_bgr.shape[:2]

        # Ground truth labels
        gt_boxes = []
        if lbl_path.exists():
            with open(lbl_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        cls_id = int(parts[0])
                        cx, cy, bw, bh = map(float, parts[1:5])
                        gt_boxes.append((cls_id, cx, cy, bw, bh))

        # Predict with RT-DETR
        t_start = time.time()
        results = model.predict(
            source=orig_bgr,
            imgsz=960,
            conf=0.563,
            device="cpu",
            verbose=False,
        )
        infer_time = time.time() - t_start
        total_time += infer_time

        annotated_img = orig_bgr.copy()
        dets = []

        for res in results:
            if res.boxes is not None:
                for box in res.boxes:
                    coords = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls_idx = int(box.cls[0].cpu().numpy())
                    cls_name = CLASS_NAMES.get(cls_idx, model.names.get(cls_idx, f"cls_{cls_idx}"))
                    dets.append({
                        "class_id": cls_idx,
                        "class_name": cls_name,
                        "conf": conf,
                        "box": [round(float(c), 1) for c in coords],
                    })

                    # Draw bounding box on annotated image
                    x1, y1, x2, y2 = map(int, coords)
                    color = CLASS_COLORS.get(cls_idx, (0, 255, 0))
                    # Convert RGB color to BGR for OpenCV drawing
                    bgr_color = (color[2], color[1], color[0])

                    cv2.rectangle(annotated_img, (x1, y1), (x2, y2), bgr_color, 2)
                    label_text = f"{cls_name} {conf:.2f}"
                    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(annotated_img, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, max(th + 6, y1)), bgr_color, -1)
                    cv2.putText(annotated_img, label_text, (x1 + 2, max(th + 2, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        # Save annotated image
        out_path = OUTPUT_DIR / f"annotated_{img_name}"
        cv2.imwrite(str(out_path), annotated_img)

        total_detections += len(dets)

        print(f"\n[IMAGE] {img_name} ({w}x{h} px)")
        print(f"  Inference time: {infer_time*1000:.1f} ms ({infer_time:.3f} s)")
        print(f"  Ground-truth classes: {[CLASS_NAMES.get(b[0], str(b[0])) for b in gt_boxes]}")
        print(f"  Detected defects ({len(dets)}):")
        if dets:
            for d in dets:
                print(f"    - {d['class_name']} (conf={d['conf']:.3f}, box=[{d['box'][0]}, {d['box'][1]}, {d['box'][2]}, {d['box'][3]}])")
        else:
            print("    (No boxes above conf=0.563 threshold; trying lower conf for diagnostics...)")
            # Diagnostic check at conf=0.25
            low_res = model.predict(source=orig_bgr, imgsz=960, conf=0.25, device="cpu", verbose=False)
            low_dets = []
            for r in low_res:
                if r.boxes is not None:
                    for b in r.boxes:
                        low_dets.append((CLASS_NAMES.get(int(b.cls[0])), float(b.conf[0])))
            print(f"    Candidates at conf=0.25: {low_dets}")

        print(f"  Saved debug image: {out_path}")

    avg_time = total_time / len(sample_files) if sample_files else 0.0
    print("\n" + "=" * 70)
    print("REALITY CHECK SUMMARY:")
    print(f"  Total test images evaluated: {len(sample_files)}")
    print(f"  Total defect boxes detected at conf=0.563: {total_detections}")
    print(f"  Average CPU inference time per image: {avg_time*1000:.1f} ms ({avg_time:.2f} s)")
    print(f"  Annotated images saved to: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
