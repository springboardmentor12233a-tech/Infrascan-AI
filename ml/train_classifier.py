from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .quality import preprocess_image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def collect_samples(data_root: Path, limit_per_class: int | None) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if not data_root.is_dir():
        raise FileNotFoundError(f"Dataset directory was not found: {data_root}")
    features: list[np.ndarray] = []
    labels: list[int] = []
    paths: list[str] = []
    for label, class_name in enumerate(("Negative", "Positive")):
        files = sorted(
            path for path in (data_root / class_name).iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )
        if limit_per_class is not None:
            files = files[:limit_per_class]
        if not files:
            raise ValueError(f"No supported images found in {data_root / class_name}")
        for path in files:
            features.append(preprocess_image(path).reshape(-1))
            labels.append(label)
            paths.append(str(path))
    return np.asarray(features, dtype=np.float32), np.asarray(labels, dtype=np.int64), paths


def train(data_root: Path, output_dir: Path, limit_per_class: int | None, test_size: float) -> dict[str, object]:
    features, labels, paths = collect_samples(data_root, limit_per_class)
    train_x, test_x, train_y, test_y, _, test_paths = train_test_split(
        features, labels, paths, test_size=test_size, random_state=42, stratify=labels
    )
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=250, random_state=42),
    )
    model.fit(train_x, train_y)
    predictions = model.predict(test_x)
    report = classification_report(
        test_y, predictions, target_names=("Negative", "Positive"), output_dict=True, zero_division=0
    )
    evaluation = {
        "task": "binary crack classification",
        "dataset_root": str(data_root),
        "samples": {"total": len(labels), "train": len(train_y), "test": len(test_y)},
        "classes": {"0": "Negative", "1": "Positive"},
        "preprocessing": {"grayscale": True, "resize": [64, 64], "standardize": True},
        "classification_report": report,
        "accuracy": float(accuracy_score(test_y, predictions)),
        "confusion_matrix": confusion_matrix(test_y, predictions).tolist(),
        "test_examples": test_paths[:10],
        "limitations": [
            "This is a baseline image-level classifier, not a detector or segmenter.",
            "Predictions are decision-support outputs and require qualified engineering review.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "baseline_classifier.pkl").open("wb") as file:
        pickle.dump(model, file)
    (output_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    return evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the InfraScan Milestone 2 baseline classifier.")
    parser.add_argument("--data-root", type=Path, default=Path("datasets/concrete_cracks/extracted"))
    parser.add_argument("--output-dir", type=Path, default=Path("ml/artifacts/classifier"))
    parser.add_argument("--limit-per-class", type=int, default=None)
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()
    evaluation = train(args.data_root, args.output_dir, args.limit_per_class, args.test_size)
    print(json.dumps({"samples": evaluation["samples"], "accuracy": evaluation["accuracy"]}, indent=2))


if __name__ == "__main__":
    main()
