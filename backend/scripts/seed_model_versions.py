"""Database seeding script for AI Model Versions.

Registers baseline trained model versions from their run_card.json files:
1. YOLOv8s RDD2022 Road Damage Detector (detection)
2. U-Net++ ResNet-34 CRACK500 Segmentation (segmentation)
"""

import json
import os
import sys
from pathlib import Path

# Add backend directory to Python path
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import BASE_DIR, settings
from app.database import Base, SessionLocal, engine
from app.models.analysis import ModelVersion


def seed_model_versions():
    """Register or update baseline model versions from their run_card.json files."""
    print("=== InfraScan: Seeding AI Model Versions ===")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    models_to_seed = []

    # 1. Segmentation Model: U-Net++ ResNet-34
    seg_run_card_candidates = [
        BASE_DIR.parent / "ml" / "models" / "segmentation" / "unetplusplus_crack500" / "run_card.json",
        BASE_DIR / ".." / "ml" / "models" / "segmentation" / "unetplusplus_crack500" / "run_card.json",
        Path(settings.SEG_WEIGHTS).parent / "run_card.json",
    ]
    seg_card_path = next((p.resolve() for p in seg_run_card_candidates if p.exists()), None)

    if seg_card_path and seg_card_path.exists():
        with open(seg_card_path, "r", encoding="utf-8") as f:
            seg_data = json.load(f)

        thresh = float(
            seg_data.get("best_validation_results", {}).get("optimal_threshold")
            or seg_data.get("threshold", 0.40)
        )
        metrics = seg_data.get("best_validation_results", {})

        models_to_seed.append({
            "model_id": "unetplusplus_crack500",
            "model_name": "U-Net++ ResNet-34 CRACK500 Segmentation",
            "task": "segmentation",
            "version": "1.0",
            "weights_path": settings.SEG_WEIGHTS,
            "threshold": thresh,
            "class_names_json": json.dumps({"0": "background", "1": "crack"}),
            "metrics_json": json.dumps(metrics),
            "is_active": True,
        })
        print(f"Loaded segmentation run card from: {seg_card_path}")
    else:
        print(f"Warning: Segmentation run_card.json not found. Using config defaults.")
        models_to_seed.append({
            "model_id": "unetplusplus_crack500",
            "model_name": "U-Net++ ResNet-34 CRACK500 Segmentation",
            "task": "segmentation",
            "version": "1.0",
            "weights_path": settings.SEG_WEIGHTS,
            "threshold": settings.SEG_THRESHOLD,
            "class_names_json": json.dumps({"0": "background", "1": "crack"}),
            "metrics_json": json.dumps({"val_dice": 0.7482, "optimal_threshold": 0.40}),
            "is_active": True,
        })

    # 2. Detection Model: YOLOv8s RDD2022
    det_run_card_candidates = [
        BASE_DIR.parent / "ml" / "detection" / "yolov8s_rdd2022" / "run_card.json",
        BASE_DIR / ".." / "ml" / "detection" / "yolov8s_rdd2022" / "run_card.json",
        Path(settings.YOLO_WEIGHTS).parent.parent / "run_card.json",
        Path(settings.YOLO_WEIGHTS).parent / "run_card.json",
    ]
    det_card_path = next((p.resolve() for p in det_run_card_candidates if p.exists()), None)

    if det_card_path and det_card_path.exists():
        with open(det_card_path, "r", encoding="utf-8") as f:
            det_data = json.load(f)

        thresh = float(det_data.get("threshold", det_data.get("confidence_threshold", 0.25)))
        classes = det_data.get("classes", {
            0: "D00 longitudinal crack",
            1: "D10 transverse crack",
            2: "D20 alligator crack",
            3: "D40 pothole",
        })
        metrics = det_data.get("metrics", {"mAP50_95": 0.22204, "mAP50": 0.45452})

        models_to_seed.append({
            "model_id": "yolov8s_rdd2022",
            "model_name": "YOLOv8s RDD2022 Road Damage Detector",
            "task": "detection",
            "version": "1.0",
            "weights_path": settings.YOLO_WEIGHTS,
            "threshold": thresh,
            "class_names_json": json.dumps(classes),
            "metrics_json": json.dumps(metrics),
            "is_active": True,
        })
        print(f"Loaded detection run card from: {det_card_path}")
    else:
        print(f"Warning: Detection run_card.json not found. Using config defaults.")
        models_to_seed.append({
            "model_id": "yolov8s_rdd2022",
            "model_name": "YOLOv8s RDD2022 Road Damage Detector",
            "task": "detection",
            "version": "1.0",
            "weights_path": settings.YOLO_WEIGHTS,
            "threshold": settings.YOLO_CONF,
            "class_names_json": json.dumps({
                0: "D00 longitudinal crack",
                1: "D10 transverse crack",
                2: "D20 alligator crack",
                3: "D40 pothole",
            }),
            "metrics_json": json.dumps({"mAP50_95": 0.22204, "mAP50": 0.45452}),
            "is_active": True,
        })

    # Upsert models into database
    try:
        for m_data in models_to_seed:
            existing = db.query(ModelVersion).filter(ModelVersion.model_id == m_data["model_id"]).first()
            if existing:
                print(f"Updating existing model version: {m_data['model_id']}")
                existing.model_name = m_data["model_name"]
                existing.task = m_data["task"]
                existing.version = m_data["version"]
                existing.weights_path = m_data["weights_path"]
                existing.threshold = m_data["threshold"]
                existing.class_names_json = m_data["class_names_json"]
                existing.metrics_json = m_data["metrics_json"]
                existing.is_active = m_data["is_active"]
            else:
                print(f"Creating new model version: {m_data['model_id']}")
                new_m = ModelVersion(**m_data)
                db.add(new_m)
        db.commit()
        print("Model versions successfully seeded.")
    except Exception as exc:
        db.rollback()
        print(f"Error seeding model versions: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_model_versions()

