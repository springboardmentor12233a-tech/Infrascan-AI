"""Fine-tune YOLOv8n on the prepared RDD2022 Czech subset.

This script downloads the official yolov8n.pt checkpoint on first use and
continues training on the local labels. The saved file models/weights/yolo_rdd.pt
is that fine-tune, not an untouched COCO model.

    backend\\venv\\Scripts\\python scripts\\ml\\prepare_yolo.py
    backend\\venv\\Scripts\\python scripts\\ml\\train_yolo.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.paths import REPORTS_DIR, YOLO_DATASET_DIR, YOLO_WEIGHTS, ensure_model_dirs  # noqa: E402

EPOCHS = 5
IMAGE_SIZE = 320
BATCH = 8


def _metric(results, name: str):
    metrics = getattr(results, "results_dict", None) or {}
    if name in metrics:
        return metrics[name]
    box = getattr(results, "box", None)
    if box is not None and hasattr(box, name):
        return getattr(box, name)
    return None


def main() -> None:
    yaml_path = YOLO_DATASET_DIR / "data.yaml"
    if not yaml_path.is_file():
        raise SystemExit("YOLO dataset is missing. Run scripts/ml/prepare_yolo.py first.")

    from ultralytics import YOLO

    ensure_model_dirs()
    model = YOLO("yolov8n.pt")
    train_results = model.train(
        data=str(yaml_path),
        epochs=EPOCHS,
        imgsz=IMAGE_SIZE,
        batch=BATCH,
        device="cpu",
        workers=0,
        project=str(ROOT / "models" / "runs"),
        name="rdd_czech",
        exist_ok=True,
        patience=4,
        verbose=True,
        plots=False,
    )
    best = Path(train_results.save_dir) / "weights" / "best.pt"
    if not best.is_file():
        best = Path(ROOT / "models" / "runs" / "rdd_czech" / "weights" / "best.pt")
    if not best.is_file():
        raise SystemExit(f"Training finished but best.pt was not found at {best}")
    shutil.copy2(best, YOLO_WEIGHTS)

    val_model = YOLO(str(YOLO_WEIGHTS))
    val_results = val_model.val(
        data=str(yaml_path),
        imgsz=IMAGE_SIZE,
        batch=BATCH,
        device="cpu",
        workers=0,
        plots=False,
        verbose=False,
    )
    summary = {
        "model_name": "YOLOv8n",
        "dataset": "RDD2022 Czech labeled subset",
        "weights": str(YOLO_WEIGHTS),
        "pretrained_start": "yolov8n.pt (COCO) fine-tuned; inference uses the fine-tuned checkpoint only",
        "config": {
            "epochs": EPOCHS,
            "image_size": IMAGE_SIZE,
            "batch_size": BATCH,
            "device": "cpu",
            "confidence_for_api": 0.25,
        },
        "validation_metrics": {
            "precision": _safe_float(_metric(val_results, "metrics/precision(B)")),
            "recall": _safe_float(_metric(val_results, "metrics/recall(B)")),
            "map50": _safe_float(_metric(val_results, "metrics/mAP50(B)")),
            "map50_95": _safe_float(_metric(val_results, "metrics/mAP50-95(B)")),
        },
        "limitations": [
            "Trained on a capped Czech subset, not the full RDD2022 release.",
            "Czech test images have no public labels, so they were not used for mAP.",
            "CPU training with few epochs. Do not treat this mAP as a leaderboard result.",
        ],
    }
    # Ultralytics also exposes mean results as a list: p, r, map50, map50-95.
    if hasattr(val_results, "mean_results"):
        means = val_results.mean_results()
        keys = ("precision", "recall", "map50", "map50_95")
        for key, value in zip(keys, means):
            if summary["validation_metrics"].get(key) is None:
                summary["validation_metrics"][key] = _safe_float(value)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "yolo_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved {YOLO_WEIGHTS}")


def _safe_float(value):
    try:
        if value is None:
            return None
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
