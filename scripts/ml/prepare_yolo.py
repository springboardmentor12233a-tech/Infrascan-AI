"""Convert RDD2022 Czech Pascal VOC XML into a YOLO detection dataset.

Only the Czech training images have public boxes. The Czech test images have
no XML, so they are not included. Original files are copied, not edited.
The prepared dataset is written under datasets/processed, which is gitignored.

    backend\\venv\\Scripts\\python scripts\\ml\\prepare_yolo.py
"""

from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml.datasets import (  # noqa: E402
    RDD_CLASS_DESCRIPTIONS,
    RDD_ID_TO_CLASS,
    iter_rdd_xml,
    parse_voc_xml,
    rdd_image_for_stem,
    voc_box_to_yolo,
)
from app.ml.paths import REPORTS_DIR, YOLO_DATASET_DIR  # noqa: E402

SEED = 42
MAX_TRAIN = 60
MAX_VAL = 20


def main() -> None:
    labeled = []
    skipped_unknown = 0
    xml_count = 0
    for xml_path in iter_rdd_xml():
        xml_count += 1
        parsed = parse_voc_xml(xml_path)
        kept = []
        for box in parsed["objects"]:
            yolo_box = voc_box_to_yolo(box, parsed["width"], parsed["height"])
            if yolo_box is None:
                if box.get("class_name") and box.get("class_id") is None:
                    skipped_unknown += 1
                continue
            kept.append((box["class_id"], yolo_box))
        if not kept:
            continue
        image_path = rdd_image_for_stem(xml_path.stem)
        if image_path is None:
            continue
        labeled.append({"stem": xml_path.stem, "image": image_path, "boxes": kept, "size": [parsed["width"], parsed["height"]]})

    if not labeled:
        raise SystemExit("No labeled RDD2022 Czech images were found.")

    rng = random.Random(SEED)
    rng.shuffle(labeled)
    val_items = labeled[:MAX_VAL]
    train_items = labeled[MAX_VAL : MAX_VAL + MAX_TRAIN]
    if len(train_items) < 10:
        raise SystemExit("Not enough labeled images to build a train split.")

    if YOLO_DATASET_DIR.exists():
        shutil.rmtree(YOLO_DATASET_DIR)
    for split, items in (("train", train_items), ("val", val_items)):
        image_dir = YOLO_DATASET_DIR / "images" / split
        label_dir = YOLO_DATASET_DIR / "labels" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for item in items:
            shutil.copy2(item["image"], image_dir / item["image"].name)
            lines = []
            for class_id, (xc, yc, bw, bh) in item["boxes"]:
                lines.append(f"{class_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
            (label_dir / f"{item['stem']}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    names = "\n".join(f"  {index}: {name}" for index, name in sorted(RDD_ID_TO_CLASS.items()))
    yaml_text = (
        f"path: {YOLO_DATASET_DIR.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n"
        f"{names}\n"
    )
    yaml_path = YOLO_DATASET_DIR / "data.yaml"
    yaml_path.write_text(yaml_text, encoding="utf-8")

    summary = {
        "dataset": "RDD2022 Czech train split",
        "xml_files_seen": xml_count,
        "images_with_boxes": len(labeled),
        "train_images_written": len(train_items),
        "val_images_written": len(val_items),
        "unknown_boxes_skipped": skipped_unknown,
        "class_map": {str(index): {"code": name, "description": RDD_CLASS_DESCRIPTIONS[name]} for index, name in RDD_ID_TO_CLASS.items()},
        "seed": SEED,
        "yaml": str(yaml_path),
        "note": "Czech test images have no public XML and were excluded. This is a capped subset for CPU training.",
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "yolo_dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
