"""Database seeding script for CODEBRIM AI Model Version.

Reads model_registry.json and run_card.json from ml/models/detection_codebrim/
and inserts or updates the model_versions row:
- model_id: A2_rtdetr_l
- model_name: CODEBRIM Defect Detector (RT-DETR-L)
- task: detection
- version: 1.0.0
- weights_path: ../ml/models/detection_codebrim/A2_rtdetr_l/weights/best.pt
- threshold: chosen_confidence (0.563)
- class_names_json: ["crack", "spallation", "exposed_bars", "efflorescence", "corrosion_stain"]
- metrics_json: labelled VALIDATION
- is_active: True

Safe to run multiple times (idempotent).
"""

import json
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


def seed_codebrim_model():
    """Register or update CODEBRIM winning model version in model_versions table."""
    print("=== InfraScan: Seeding CODEBRIM AI Model Version ===")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Locate model_registry.json
        reg_candidates = [
            BASE_DIR.parent / "ml" / "models" / "detection_codebrim" / "model_registry.json",
            settings.ml_models_path / "models" / "detection_codebrim" / "model_registry.json",
            Path(r"D:\Infosys springboards\infrascan\ml\models\detection_codebrim\model_registry.json"),
        ]
        reg_path = next((p for p in reg_candidates if p.exists()), None)
        if not reg_path:
            raise FileNotFoundError("Could not find model_registry.json in ml/models/detection_codebrim/")

        with open(reg_path, "r", encoding="utf-8") as f:
            reg_data = json.load(f)

        model_name = reg_data.get("model_name", "A2_rtdetr_l")
        weights_rel = reg_data.get("weights_file", f"{model_name}/weights/best.pt")
        weights_path = f"../ml/models/detection_codebrim/{weights_rel}".replace("\\", "/")
        chosen_conf = float(reg_data.get("chosen_confidence", 0.563))
        class_names = reg_data.get("class_names", [
            "crack", "spallation", "exposed_bars", "efflorescence", "corrosion_stain"
        ])
        raw_val_metrics = reg_data.get("validation_metrics", {})

        # Also check run_card.json if present for additional details
        run_card_path = reg_path.parent / model_name / "run_card.json"
        if run_card_path.exists():
            with open(run_card_path, "r", encoding="utf-8") as f:
                card_data = json.load(f)
                if "validation_precision" in card_data:
                    raw_val_metrics["precision"] = card_data["validation_precision"]
                    raw_val_metrics["recall"] = card_data["validation_recall"]
                    raw_val_metrics["mAP50"] = card_data["validation_mAP50"]
                    raw_val_metrics["mAP50_95"] = card_data["validation_mAP50_95"]

        # Ensure validation metrics are explicitly labelled VALIDATION
        metrics_dict = {
            "label": "VALIDATION",
            "VALIDATION": raw_val_metrics,
            "source": "model_registry.json",
            "chosen_confidence": chosen_conf,
        }

        # Check existing row
        existing = db.query(ModelVersion).filter(ModelVersion.model_id == model_name).first()
        if existing:
            print(f"Updating existing ModelVersion record for '{model_name}'...")
            existing.model_name = "CODEBRIM Defect Detector (RT-DETR-L)"
            existing.task = "detection"
            existing.version = "1.0.0"
            existing.weights_path = weights_path
            existing.threshold = chosen_conf
            existing.class_names_json = json.dumps(class_names)
            existing.metrics_json = json.dumps(metrics_dict)
            existing.is_active = True
        else:
            print(f"Inserting new ModelVersion record for '{model_name}'...")
            new_mv = ModelVersion(
                model_id=model_name,
                model_name="CODEBRIM Defect Detector (RT-DETR-L)",
                task="detection",
                version="1.0.0",
                weights_path=weights_path,
                threshold=chosen_conf,
                class_names_json=json.dumps(class_names),
                metrics_json=json.dumps(metrics_dict),
                is_active=True,
            )
            db.add(new_mv)

        db.commit()
        print(f"[OK] Successfully registered CODEBRIM model '{model_name}' with threshold {chosen_conf}.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to seed CODEBRIM model version: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_codebrim_model()
