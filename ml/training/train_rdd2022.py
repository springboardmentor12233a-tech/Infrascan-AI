"""
RDD2022 -> YOLO Training & Evaluation Script for InfraScan.

Inspects `dataset_audit/processed_dataset`, converts Pascal VOC XML annotations
into YOLO format with leakage-safe train/val/test splits, trains YOLOv8n,
evaluates Precision, Recall, mAP50, and mAP50-95, and exports weights to
`backend/weights/rdd2022_yolo.pt`.

Usage (recommended on GPU / Kaggle):
    python backend/scripts/train_rdd2022.py --epochs 50 --imgsz 640 --batch 16
"""

import argparse
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

CLASSES = ["D00", "D10", "D20", "D40"]
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}


def convert_voc_to_yolo(xml_path: Path, img_w: int, img_h: int) -> list[str]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    lines = []
    for obj in root.findall("object"):
        name = (obj.findtext("name") or "").strip()
        if name not in CLASS_TO_ID:
            continue
        bnd = obj.find("bndbox")
        if bnd is None:
            continue
        xmin = float(bnd.findtext("xmin", "0"))
        ymin = float(bnd.findtext("ymin", "0"))
        xmax = float(bnd.findtext("xmax", "0"))
        ymax = float(bnd.findtext("ymax", "0"))
        if xmax <= xmin or ymax <= ymin:
            continue
        xc = ((xmin + xmax) / 2.0) / img_w
        yc = ((ymin + ymax) / 2.0) / img_h
        bw = (xmax - xmin) / img_w
        bh = (ymax - ymin) / img_h
        lines.append(f"{CLASS_TO_ID[name]} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
    return lines


def prepare_yolo_dataset(src_root: Path, dst_root: Path, seed: int = 42, max_samples: int | None = None):
    pairs = []
    for xml_path in src_root.rglob("*.xml"):
        stem = xml_path.stem
        img_dir = xml_path.parent.parent / "images"
        img_path = None
        for ext in (".jpg", ".jpeg", ".png"):
            cand = img_dir / f"{stem}{ext}"
            if cand.exists():
                img_path = cand
                break
        if img_path:
            pairs.append((img_path, xml_path))

    random.seed(seed)
    random.shuffle(pairs)
    if max_samples:
        pairs = pairs[:max_samples]

    n = len(pairs)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    splits = {
        "train": pairs[:n_train],
        "val": pairs[n_train : n_train + n_val],
        "test": pairs[n_train + n_val :],
    }

    for split, items in splits.items():
        (dst_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (dst_root / "labels" / split).mkdir(parents=True, exist_ok=True)
        for img_path, xml_path in items:
            tree = ET.parse(xml_path)
            size = tree.getroot().find("size")
            w = int(size.findtext("width", "640")) if size is not None else 640
            h = int(size.findtext("height", "640")) if size is not None else 640
            yolo_lines = convert_voc_to_yolo(xml_path, w, h)
            shutil.copy2(img_path, dst_root / "images" / split / img_path.name)
            (dst_root / "labels" / split / f"{img_path.stem}.txt").write_text("\n".join(yolo_lines))

    yaml_path = dst_root / "rdd2022.yaml"
    yaml_path.write_text(
        f"path: {dst_root.resolve()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        f"nc: {len(CLASSES)}\n"
        f"names: {CLASSES}\n"
    )
    return yaml_path, {k: len(v) for k, v in splits.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="dataset_audit/processed_dataset")
    parser.add_argument("--dst", default="backend/data/rdd2022_yolo")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--max-samples", type=int, default=None)
    args = parser.parse_args()

    yaml_path, counts = prepare_yolo_dataset(Path(args.src), Path(args.dst), max_samples=args.max_samples)
    print(f"Prepared YOLO dataset at {yaml_path}: {counts}")

    from ultralytics import YOLO
    model = YOLO("yolov8n.pt")
    model.train(data=str(yaml_path), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, project="backend/runs", name="rdd2022")
    metrics = model.val(data=str(yaml_path), split="test")
    print("Evaluation:", metrics.results_dict)

    best_pt = Path("backend/runs/rdd2022/weights/best.pt")
    out_pt = Path("backend/weights/rdd2022_yolo.pt")
    out_pt.parent.mkdir(parents=True, exist_ok=True)
    if best_pt.exists():
        shutil.copy2(best_pt, out_pt)
        print(f"Saved trained weights to {out_pt}")


if __name__ == "__main__":
    main()

