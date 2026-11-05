from __future__ import annotations

import argparse
from pathlib import Path


def validate_dataset_yaml(dataset_yaml: Path) -> None:
    if not dataset_yaml.is_file():
        raise FileNotFoundError(
            f"YOLO dataset configuration was not found: {dataset_yaml}. "
            "Provide images with matching YOLO bounding-box label files."
        )
    text = dataset_yaml.read_text(encoding="utf-8")
    if "train:" not in text or "val:" not in text:
        raise ValueError("YOLO dataset YAML must define both train and val image splits.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Milestone 2 YOLO detector.")
    parser.add_argument("--dataset-yaml", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("ml/artifacts/detection"))
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--model", default="yolo11n.pt")
    args = parser.parse_args()
    validate_dataset_yaml(args.dataset_yaml)
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError(
            "YOLO training requires the optional ML dependencies. "
            "Install them with: python -m pip install -r ml\\requirements-ml-optional.txt"
        ) from exc
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.model)
    model.train(data=str(args.dataset_yaml), epochs=args.epochs, project=str(args.output_dir), name="yolo_baseline")


if __name__ == "__main__":
    main()
