"""InfraScan YOLO Detection Training Pipeline.

Provides automated training for Ultralytics YOLO models (YOLOv8s, YOLO11s)
on the RDD2022 road damage dataset, with deterministic settings, Google Drive
persistence, automatic checkpoint resumption, and run card generation.
"""

import datetime
import json
import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional

from ml.detection import config


def make_data_yaml(
    data_root: str,
    out_path: Optional[str] = None,
) -> str:
    """Generate and write a YOLO data.yaml configuration with absolute paths.

    Args:
        data_root: Absolute root path of the dataset (e.g., '/content/rdd2022_yolo_small').
        out_path: Optional destination path for data.yaml. If None, saves to <data_root>/data.yaml.

    Returns:
        The absolute path to the generated data.yaml file.
    """
    data_root_clean = str(Path(data_root).as_posix())
    if out_path is None:
        out_path = str(Path(data_root) / "data.yaml")

    yaml_lines = [
        f"path: {data_root_clean}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        "names:",
    ]
    for cid, cname in sorted(config.CLASS_NAMES.items()):
        yaml_lines.append(f"  {cid}: {cname}")

    yaml_content = "\n".join(yaml_lines) + "\n"

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    print(f"[OK] Generated dataset YAML at: {out_file}")
    return str(out_file)


def train(
    model_weights: str,
    data_yaml: str,
    project_dir: str,
    run_name: str,
    debug: bool = False,
    epochs: Optional[int] = None,
    batch_size: Optional[int] = None,
    seed: int = config.RANDOM_SEED,
) -> Any:
    """Train a YOLO model using Ultralytics with InfraScan standardized settings.

    Args:
        model_weights: Initial weights file or model identifier (e.g., 'yolov8s.pt').
        data_yaml: Path to data.yaml dataset configuration.
        project_dir: Root directory for runs (typically on Google Drive).
        run_name: Name of the run folder (e.g., 'yolov8s_rdd2022').
        debug: If True, runs 1 epoch on 10% data fraction for fast sanity check.
        epochs: Number of epochs (overrides default/debug if provided).
        batch_size: Batch size (defaults to config.BATCH_SIZE).
        seed: Random seed for reproducibility.

    Returns:
        Ultralytics training results object.
    """
    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise ImportError(
            "Ultralytics is required for training. Install it via 'pip install ultralytics'."
        ) from e

    import torch

    project_path = Path(project_dir)
    run_dir = project_path / run_name
    last_pt = run_dir / "weights" / "last.pt"

    # Hyperparameters
    actual_epochs = epochs if epochs is not None else (config.DEBUG_EPOCHS if debug else config.EPOCHS)
    actual_batch = batch_size if batch_size is not None else config.BATCH_SIZE
    fraction = config.DEBUG_FRACTION if debug else 1.0

    print("=" * 70)
    print(f"InfraScan YOLO Training: {run_name}")
    print(f"  Model Initial Weights : {model_weights}")
    print(f"  Data Configuration    : {data_yaml}")
    print(f"  Output Project Dir    : {project_dir}")
    print(f"  Epochs                : {actual_epochs}")
    print(f"  Batch Size            : {actual_batch}")
    print(f"  Image Size            : {config.IMAGE_SIZE}")
    print(f"  Patience (EarlyStop)  : {config.PATIENCE}")
    print(f"  Seed                  : {seed}")
    print(f"  Deterministic         : {config.DETERMINISTIC}")
    print(f"  Save Period           : {config.SAVE_PERIOD} (best.pt and last.pt only)")
    print(f"  Flip UD Augmentation  : {config.FLIPUD}")
    print(f"  Debug Mode            : {debug} (fraction={fraction})")
    print("=" * 70)

    # Check for resumption
    if last_pt.exists():
        print(f"[RESUME] Found existing last checkpoint at {last_pt}. Resuming training...")
        model = YOLO(str(last_pt))
        train_args = {
            "resume": True,
        }
    else:
        print(f"[INIT] Initializing new training run from {model_weights}...")
        model = YOLO(model_weights)
        train_args = {
            "data": data_yaml,
            "imgsz": config.IMAGE_SIZE,
            "epochs": actual_epochs,
            "batch": actual_batch,
            "patience": config.PATIENCE,
            "seed": seed,
            "deterministic": config.DETERMINISTIC,
            "workers": config.WORKERS,
            "amp": config.AMP,
            "cos_lr": config.COS_LR,
            "project": str(project_path),
            "name": run_name,
            "exist_ok": True,
            "save_period": config.SAVE_PERIOD,
            "flipud": config.FLIPUD,
            "fraction": fraction,
        }

    # Execute training
    results = model.train(**train_args)

    # Generate Run Card
    try:
        import ultralytics
        ultralytics_ver = getattr(ultralytics, "__version__", "unknown")
    except Exception:
        ultralytics_ver = "unknown"

    # Count dataset images if accessible
    data_counts: Dict[str, int] = {}
    try:
        with open(data_yaml, "r", encoding="utf-8") as f:
            yaml_raw = f.read()
        # Parse data root from yaml
        for line in yaml_raw.splitlines():
            if line.strip().startswith("path:"):
                d_root = line.split(":", 1)[1].strip()
                for split in ["train", "val", "test"]:
                    split_img_dir = Path(d_root) / "images" / split
                    if split_img_dir.exists():
                        data_counts[split] = len(list(split_img_dir.glob("*.jpg")))
                break
    except Exception as e:
        data_counts = {"error": str(e)}

    # Hardware metadata
    hw_info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cuda_available": torch.cuda.is_available(),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }

    run_card: Dict[str, Any] = {
        "run_name": run_name,
        "model_weights": model_weights,
        "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "torch_version": torch.__version__,
        "ultralytics_version": ultralytics_ver,
        "seed": seed,
        "debug_mode": debug,
        "hyperparameters": {
            "imgsz": config.IMAGE_SIZE,
            "epochs": actual_epochs,
            "batch_size": actual_batch,
            "patience": config.PATIENCE,
            "deterministic": config.DETERMINISTIC,
            "amp": config.AMP,
            "cos_lr": config.COS_LR,
            "save_period": config.SAVE_PERIOD,
            "flipud": config.FLIPUD,
            "fraction": fraction,
            "workers": config.WORKERS,
        },
        "data_yaml_path": str(data_yaml),
        "dataset_counts": data_counts,
        "classes": config.CLASS_NAMES,
        "hardware": hw_info,
    }

    card_path = run_dir / "run_card.json"
    card_path.parent.mkdir(parents=True, exist_ok=True)
    with open(card_path, "w", encoding="utf-8") as f:
        json.dump(run_card, f, indent=2)

    print(f"[OK] Training complete. Run card written to: {card_path}")
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="InfraScan YOLO Training")
    parser.add_argument("--weights", type=str, default="yolov8s.pt", help="Base weights")
    parser.add_argument("--data", type=str, default="/content/rdd2022_yolo_small/data.yaml")
    parser.add_argument("--project", type=str, default="/content/drive/MyDrive/infrascan/models/detection")
    parser.add_argument("--name", type=str, default="yolov8s_rdd2022")
    parser.add_argument("--debug", action="store_true", help="Run 1 epoch debug")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch", type=int, default=None)
    args = parser.parse_args()

    train(
        model_weights=args.weights,
        data_yaml=args.data,
        project_dir=args.project,
        run_name=args.name,
        debug=args.debug,
        epochs=args.epochs,
        batch_size=args.batch,
    )

