from __future__ import annotations

import argparse
import json
from pathlib import Path

from .quality import assess_image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess image quality for the Milestone 2 dataset.")
    parser.add_argument("--data-root", type=Path, default=Path("datasets/concrete_cracks/extracted"))
    parser.add_argument("--output", type=Path, default=Path("ml/artifacts/quality-report.json"))
    parser.add_argument("--limit-per-class", type=int, default=None)
    args = parser.parse_args()
    results = []
    for class_name in ("Negative", "Positive"):
        files = sorted(
            path for path in (args.data_root / class_name).iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )
        if args.limit_per_class is not None:
            files = files[:args.limit_per_class]
        results.extend(assess_image(path).to_dict() | {"label": class_name} for path in files)
    if not results:
        raise ValueError(f"No supported images found below {args.data_root}")
    summary = {
        "total_images": len(results),
        "by_class": {
            label: sum(1 for result in results if result["label"] == label)
            for label in ("Negative", "Positive")
        },
        "low_light": sum(result["is_low_light"] for result in results),
        "low_contrast": sum(result["is_low_contrast"] for result in results),
        "blurry": sum(result["is_blurry"] for result in results),
        "images": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "images"}, indent=2))


if __name__ == "__main__":
    main()
