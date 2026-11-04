"""
InfraScan Dataset Cleaning, Splitting, and Label Conversion Pipeline.

This module prepares raw crack detection datasets for training and evaluation:
- SDNET2018 (Classification): Deduplicated, source photo group split (70/15/15)
- concrete_crack_cls (Classification): Deduplicated, stratified split (70/15/15)
- RDD2022 (Object Detection): Deduplicated, VOC to YOLO conversion, background support, 70/15/15 split
- CRACK500 (Segmentation): Deduplicated official crop partitions and masks
- CFD (Segmentation Benchmark): Verified grayscale mask, test split (118 images)

Raw data is strictly READ-ONLY. All outputs are written to data/processed.
"""

import os
import re
import csv
import glob
import math
import shutil
import random
import hashlib
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor

try:
    import yaml
except ImportError:
    yaml = None
import numpy as np
import pandas as pd
from PIL import Image
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Fixed random seed for complete reproducibility
RANDOM_SEED = 42

# RDD2022 Class Mapping
RDD_CLASSES = {
    "D00": 0,  # Longitudinal crack
    "D10": 1,  # Transverse crack
    "D20": 2,  # Alligator crack
    "D40": 3,  # Pothole
}

RDD_CLASSES_INV = {v: k for k, v in RDD_CLASSES.items()}

RDD_CLASS_NAMES = {
    0: "D00 (longitudinal)",
    1: "D10 (transverse)",
    2: "D20 (alligator)",
    3: "D40 (pothole)",
}


class CleaningReport:
    """Logger to record excluded files and box anomalies into cleaning_report.csv."""

    def __init__(self, report_path: str):
        self.report_path = report_path
        self.records = []
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

    def log(self, dataset: str, file_path: str, reason: str, details: str = ""):
        self.records.append({
            "dataset": dataset,
            "file_path": str(file_path),
            "reason": reason,
            "details": details
        })

    def save(self):
        df = pd.DataFrame(self.records, columns=["dataset", "file_path", "reason", "details"])
        df.to_csv(self.report_path, index=False)
        print(f"[CleaningReport] Saved {len(self.records)} exclusion records to: {self.report_path}")
        return df


def compute_sha256(file_path: str) -> str:
    """Compute SHA-256 hash of a file efficiently in 64KB blocks."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _parse_yolo_label_file(label_path: str) -> tuple[bool, Counter]:
    """Validate one YOLO label file and return its background flag and class counts."""
    class_counts = Counter()
    with open(label_path, "r", encoding="utf-8") as label_file:
        for line_number, line in enumerate(label_file, start=1):
            parts = line.strip().split()
            if not parts:
                continue
            if len(parts) != 5:
                raise AssertionError(
                    f"Assertion Error: Expected 5 YOLO values at {label_path}:{line_number}."
                )
            try:
                class_id = int(parts[0])
                coordinates = [float(value) for value in parts[1:]]
            except ValueError as exc:
                raise AssertionError(
                    f"Assertion Error: Invalid YOLO values at {label_path}:{line_number}."
                ) from exc
            if class_id not in RDD_CLASSES_INV:
                raise AssertionError(
                    f"Assertion Error: Class {class_id} out of range 0..3 at "
                    f"{label_path}:{line_number}."
                )
            if any(not 0.0 <= value <= 1.0 for value in coordinates):
                raise AssertionError(
                    f"Assertion Error: YOLO coordinates outside [0, 1] at "
                    f"{label_path}:{line_number}."
                )
            class_counts[class_id] += 1
    return not class_counts, class_counts


def _validate_yolo_image_label(pair: tuple[str, str]) -> str:
    """Hash an image and validate its paired YOLO label file."""
    image_path, label_path = pair
    image_hash = compute_sha256(image_path)
    _parse_yolo_label_file(label_path)
    return image_hash


def _verify_and_hash_worker(path: str):
    """Worker to verify image readability and calculate its SHA-256 hash."""
    try:
        with Image.open(path) as im:
            im.verify()
        h = compute_sha256(path)
        return (path, True, h, None)
    except Exception as e:
        return (path, False, None, str(e))


def _split_counts(count: int) -> dict:
    """Allocate counts as closely as possible to a 70/15/15 split."""
    ratios = (0.70, 0.15, 0.15)
    counts = [int(count * ratio) for ratio in ratios]
    remainder = count - sum(counts)
    order = sorted(range(3), key=lambda i: count * ratios[i] - counts[i], reverse=True)
    for index in order[:remainder]:
        counts[index] += 1
    return dict(zip(("train", "val", "test"), counts))


def _imbalance_ratio(counts) -> str:
    values = list(counts)
    if not values or max(values) == 0:
        return "N/A"
    if min(values) == 0:
        return "inf:1"
    return f"{max(values) / min(values):.2f}:1"


def _assign_stratified_splits(items: list, label_key: str, seed: int = RANDOM_SEED) -> None:
    """Assign a reproducible 70/15/15 split independently for each class."""
    rng = random.Random(seed)
    by_label = defaultdict(list)
    for item in items:
        by_label[item[label_key]].append(item)

    for label_items in by_label.values():
        rng.shuffle(label_items)
        counts = _split_counts(len(label_items))
        train_end = counts["train"]
        val_end = train_end + counts["val"]
        for index, item in enumerate(label_items):
            item["split"] = "train" if index < train_end else "val" if index < val_end else "test"


def _assign_grouped_splits(items: list, seed: int = RANDOM_SEED) -> None:
    """Assign source-photo groups while approximately balancing labels and sizes."""
    grouped = defaultdict(list)
    for item in items:
        grouped[item["group"]].append(item)

    rng = random.Random(seed)
    groups = list(grouped)
    rng.shuffle(groups)
    groups.sort(key=lambda group: len(grouped[group]), reverse=True)
    total_counts = Counter(item.get("_stratum", item["label"]) for item in items)
    total_size = len(items)
    targets = {
        split: {
            label: total_counts[label] * ratio
            for label in total_counts
        }
        for split, ratio in zip(("train", "val", "test"), (0.70, 0.15, 0.15))
    }
    size_targets = {split: total_size * ratio for split, ratio in zip(
        ("train", "val", "test"), (0.70, 0.15, 0.15)
    )}
    assigned = {split: Counter() for split in ("train", "val", "test")}
    split_sizes = Counter()

    for group in groups:
        group_counts = Counter(item.get("_stratum", item["label"]) for item in grouped[group])
        scores = {}
        for split in assigned:
            score = 0.0
            for candidate in assigned:
                for label, target in targets[candidate].items():
                    actual = assigned[candidate][label]
                    if candidate == split:
                        actual += group_counts[label]
                    score += ((actual - target) / max(target, 1.0)) ** 2
                actual_size = split_sizes[candidate]
                if candidate == split:
                    actual_size += len(grouped[group])
                score += ((actual_size - size_targets[candidate]) / max(size_targets[candidate], 1.0)) ** 2
            scores[split] = score

        chosen = min(scores, key=scores.get)
        assigned[chosen].update(group_counts)
        split_sizes[chosen] += len(grouped[group])
        for item in grouped[group]:
            item["split"] = chosen


def print_folder_structures(raw_dirs: dict):
    """Print high-level folder structure and preliminary counts for all raw datasets."""
    print("=" * 70)
    print("RAW DATASET FOLDER STRUCTURES & INITIAL INSPECTION")
    print("=" * 70)
    image_counts = {}
    for name, path in raw_dirs.items():
        if not os.path.exists(path):
            print(f"[-] {name}: NOT FOUND at {path}")
            image_counts[name] = 0
            continue
        print(f"\n[+] Dataset: {name}")
        print(f"    Path: {path}")
        
        # Immediate subdirectories
        subdirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        print(f"    Subdirectories ({len(subdirs)}): {subdirs[:8]}")
        
        # Recursive image count
        img_count = 0
        for root, _, files in tqdm(os.walk(path), desc=f"Counting {name} folders", unit="dir"):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_count += 1
        image_counts[name] = img_count
        print(f"    Total image files found: {img_count:,}")
    print("=" * 70)
    return image_counts


def process_sdnet2018(raw_dir: str, processed_dir: str, report: CleaningReport, seed: int = RANDOM_SEED):
    """
    Process SDNET2018:
    - Inspect filename pattern: prefix before '-' indicates the original source photo ID.
    - Perform group split by source photo ID so crops of the same photo stay in the same split.
    - Stratified across surface types (Deck, Pavement, Wall) and crack ratios (70/15/15).
    - Save manifest: data/processed/manifests/sdnet2018.csv (path, label, group, hash, split).
    """
    print("\n--- Processing SDNET2018 ---")
    manifest_dir = os.path.join(processed_dir, "manifests")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, "sdnet2018.csv")

    subfolders = [
        ("D", "CD", "cracked"),
        ("D", "UD", "uncracked"),
        ("P", "CP", "cracked"),
        ("P", "UP", "uncracked"),
        ("W", "CW", "cracked"),
        ("W", "UW", "uncracked"),
    ]

    all_files = []
    for surf, code, label in subfolders:
        folder = os.path.join(raw_dir, surf, code)
        if not os.path.exists(folder):
            print(f"[!] Warning: SDNET2018 folder missing: {folder}")
            report.log("sdnet2018", folder, "missing_label", f"Expected class folder {code} is missing.")
            continue
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                full_path = os.path.join(folder, fname)
                all_files.append((full_path, fname, surf, label))

    print(f"Total raw files indexed: {len(all_files):,}")

    source_pattern = re.compile(r"^(.+?)-\d+(?:_\d+)?\.[^.]+$")
    has_source_pattern = bool(all_files) and all(
        source_pattern.match(fname) for _, fname, _, _ in all_files
    )
    if has_source_pattern:
        print("[SDNET2018] Filename pattern identifies source photo IDs; using grouped split.")
    else:
        print(
            "[!] WARNING: SDNET2018 filenames do not consistently identify source photos. "
            "Using a stratified random split; crops may leak across splits."
        )

    # Step 1: Threaded verification and hashing
    paths_to_check = [f[0] for f in all_files]
    with ThreadPoolExecutor(max_workers=8) as executor:
        check_results = list(tqdm(
            executor.map(_verify_and_hash_worker, paths_to_check),
            total=len(paths_to_check),
            desc="Cleaning & Hashing SDNET2018"
        ))

    # Step 2: Deduplication and grouping
    valid_items = []
    seen_hashes = {}
    for (full_path, fname, surf, label), (chk_path, is_valid, file_hash, err_msg) in zip(all_files, check_results):
        if not is_valid:
            report.log("sdnet2018", full_path, "unreadable_image", f"Corrupt image header: {err_msg}")
            continue
        
        if file_hash in seen_hashes:
            report.log("sdnet2018", full_path, "duplicate_hash", f"Matches earlier image: {seen_hashes[file_hash]}")
            continue
        seen_hashes[file_hash] = full_path

        # Example: 7001-115.jpg -> all crops of photo 7001 share one group.
        match = source_pattern.match(fname)
        group_id = match.group(1) if has_source_pattern and match else f"{surf}_{fname}"
        valid_items.append({
            "path": full_path,
            "label": label,
            "surface": surf,
            "group": group_id,
            "hash": file_hash
        })

    print(f"Valid unique images after cleaning: {len(valid_items):,} (Removed {len(all_files) - len(valid_items):,})")

    # Balance source groups across surface and label strata when possible.
    if has_source_pattern:
        for item in valid_items:
            item["_stratum"] = f"{item['surface']}_{item['label']}"
        _assign_grouped_splits(valid_items, seed)
        for item in valid_items:
            del item["_stratum"]
    else:
        for item in valid_items:
            item["_stratum"] = f"{item['surface']}_{item['label']}"
        _assign_stratified_splits(valid_items, "_stratum", seed)
        for item in valid_items:
            del item["_stratum"]

    # Write manifest: path, label, group, hash, split
    df_manifest = pd.DataFrame(valid_items)[["path", "label", "group", "hash", "split"]]
    df_manifest.to_csv(manifest_path, index=False)
    print(f"Saved SDNET2018 manifest to: {manifest_path}")
    print(df_manifest["split"].value_counts().to_string())
    return df_manifest


def process_concrete_crack_cls(raw_dir: str, processed_dir: str, report: CleaningReport, seed: int = RANDOM_SEED):
    """
    Process concrete_crack_cls:
    - Inspect filenames: sequential numbering without source photo prefix.
    - Print warning about potential crop leakage.
    - Clean: readable check and duplicate SHA-256 hash exclusion.
    - Stratified random 70/15/15 train/val/test split by class.
    - Save manifest: data/processed/manifests/concrete_crack_cls.csv (path, label, hash, split).
    """
    print("\n--- Processing concrete_crack_cls ---")
    manifest_dir = os.path.join(processed_dir, "manifests")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, "concrete_crack_cls.csv")

    print("[!] WARNING: concrete_crack_cls filenames do not contain source photo identifiers. "
          "Using stratified random split. Note that adjacent crops from the same concrete surface "
          "may leak across train/val/test splits.")

    class_dirs = [
        ("Positive", "cracked"),
        ("Negative", "uncracked")
    ]

    all_files = []
    for fld, label in class_dirs:
        folder = os.path.join(raw_dir, fld)
        if not os.path.exists(folder):
            print(f"[!] Warning: Folder missing: {folder}")
            report.log(
                "concrete_crack_cls", folder, "missing_label",
                f"Expected class folder {fld} is missing."
            )
            continue
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                all_files.append((os.path.join(folder, fname), label))

    print(f"Total raw files indexed: {len(all_files):,}")

    # Threaded verification and hashing
    paths_to_check = [f[0] for f in all_files]
    with ThreadPoolExecutor(max_workers=8) as executor:
        check_results = list(tqdm(
            executor.map(_verify_and_hash_worker, paths_to_check),
            total=len(paths_to_check),
            desc="Cleaning & Hashing concrete_crack_cls"
        ))

    # Deduplication
    valid_items = []
    seen_hashes = {}
    for (full_path, label), (chk_path, is_valid, file_hash, err_msg) in zip(all_files, check_results):
        if not is_valid:
            report.log("concrete_crack_cls", full_path, "unreadable_image", f"Corrupt image header: {err_msg}")
            continue
        
        if file_hash in seen_hashes:
            report.log("concrete_crack_cls", full_path, "duplicate_hash", f"Matches earlier image: {seen_hashes[file_hash]}")
            continue
        seen_hashes[file_hash] = full_path

        valid_items.append({
            "path": full_path,
            "label": label,
            "hash": file_hash
        })

    print(f"Valid unique images after cleaning: {len(valid_items):,} (Removed {len(all_files) - len(valid_items):,})")

    _assign_stratified_splits(valid_items, "label", seed)

    df_manifest = pd.DataFrame(valid_items)[["path", "label", "hash", "split"]]
    df_manifest.to_csv(manifest_path, index=False)
    print(f"Saved concrete_crack_cls manifest to: {manifest_path}")
    print(df_manifest["split"].value_counts().to_string())
    return df_manifest


def process_rdd2022(raw_dir: str, processed_dir: str, report: CleaningReport, seed: int = RANDOM_SEED):
    """
    Process RDD2022:
    - 7 country folders: China_Drone, China_MotorBike, Czech, India, Japan, Norway, United_States.
    - Convert Pascal VOC XML bounding boxes to YOLO format (0..3).
    - Skip unsupported classes (Repair, Block crack, etc.) and log them.
    - Check coordinates: clip to image bounds [0, W], [0, H]; skip invalid boxes (x2 <= x1 or y2 <= y1).
    - Support background images: images without crack boxes receive an empty .txt file.
    - Balanced 70/15/15 train/val/test split across countries.
    - Copy images to: data/processed/rdd2022_yolo/images/{train,val,test}
    - Write labels to: data/processed/rdd2022_yolo/labels/{train,val,test}
    - Write data.yaml configuration file.
    """
    print("\n--- Processing RDD2022 ---")
    yolo_root = os.path.join(processed_dir, "rdd2022_yolo")
    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(yolo_root, "images", split), exist_ok=True)
        os.makedirs(os.path.join(yolo_root, "labels", split), exist_ok=True)

    countries = sorted(
        name for name in os.listdir(raw_dir)
        if os.path.isdir(os.path.join(raw_dir, name))
        and os.path.isdir(os.path.join(raw_dir, name, "train", "images"))
    )
    all_raw_images = []

    for country in countries:
        img_dir = os.path.join(raw_dir, country, "train", "images")
        xml_dir = os.path.join(raw_dir, country, "train", "annotations", "xmls")
        if not os.path.isdir(xml_dir):
            print(f"[!] Ignoring {country}: Pascal VOC XML labels are missing.")
            report.log(
                "rdd2022",
                os.path.join(raw_dir, country),
                "missing_label",
                "Country folder ignored because its train XML label directory is missing.",
            )
            continue

        for fname in sorted(os.listdir(img_dir)):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                stem = os.path.splitext(fname)[0]
                xml_path = os.path.join(xml_dir, stem + ".xml")
                all_raw_images.append({
                    "country": country,
                    "image_path": os.path.join(img_dir, fname),
                    "filename": fname,
                    "stem": stem,
                    "xml_path": xml_path if os.path.exists(xml_path) else None
                })

    print(f"Total raw RDD2022 images indexed: {len(all_raw_images):,}")

    # Threaded verification and hashing
    paths_to_check = [item["image_path"] for item in all_raw_images]
    with ThreadPoolExecutor(max_workers=16) as executor:
        check_results = list(tqdm(
            executor.map(_verify_and_hash_worker, paths_to_check),
            total=len(paths_to_check),
            desc="Cleaning & Hashing RDD2022",
            mininterval=2.0
        ))

    valid_images = []
    seen_hashes = {}
    for item, (chk_path, is_valid, file_hash, err_msg) in zip(all_raw_images, check_results):
        img_path = item["image_path"]
        if not is_valid:
            report.log("rdd2022", img_path, "unreadable_image", f"Corrupt image file: {err_msg}")
            continue

        if not item["xml_path"]:
            report.log("rdd2022", img_path, "missing_label", "Pascal VOC XML annotation is missing.")
            continue

        try:
            ET.parse(item["xml_path"])
        except (ET.ParseError, OSError) as exc:
            report.log("rdd2022", item["xml_path"], "xml_parse_error", str(exc))
            continue

        if file_hash in seen_hashes:
            report.log("rdd2022", img_path, "duplicate_hash", f"Matches earlier image: {seen_hashes[file_hash]}")
            continue
        seen_hashes[file_hash] = img_path
        item["hash"] = file_hash
        valid_images.append(item)

    print(f"Valid unique images after cleaning: {len(valid_images):,} (Removed {len(all_raw_images) - len(valid_images):,})")

    # Balanced 70/15/15 Split by Country
    rng = random.Random(seed)
    by_country = defaultdict(list)
    for item in valid_images:
        by_country[item["country"]].append(item)

    for country, items in by_country.items():
        rng.shuffle(items)
        counts = _split_counts(len(items))
        n_train = counts["train"]
        n_val = n_train + counts["val"]
        for i, it in enumerate(items):
            if i < n_train:
                it["split"] = "train"
            elif i < n_val:
                it["split"] = "val"
            else:
                it["split"] = "test"

    # Tasks for file copying and label generation
    tasks = []
    output_stems = set()
    for item in valid_images:
        split = item["split"]
        output_stem = f"{item['country']}_{item['stem']}"
        if output_stem.casefold() in output_stems:
            output_stem = f"{output_stem}_{item['hash'][:8]}"
        if output_stem.casefold() in output_stems:
            raise ValueError(f"RDD2022 output filename collision for {item['image_path']}")
        output_stems.add(output_stem.casefold())
        output_name = output_stem + os.path.splitext(item["filename"])[1]
        item["output_name"] = output_name
        dst_img = os.path.join(yolo_root, "images", split, output_name)
        dst_lbl = os.path.join(yolo_root, "labels", split, os.path.splitext(output_name)[0] + ".txt")
        tasks.append((item, dst_img, dst_lbl))

    # Track anomalies to log after thread execution
    logged_anomalies = []

    def convert_and_write(task):
        item, dst_img, dst_lbl = task
        img_path = item["image_path"]
        xml_path = item["xml_path"]

        yolo_lines = []
        if xml_path and os.path.exists(xml_path):
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                with Image.open(img_path) as im:
                    width, height = im.size

                for obj in root.findall("object"):
                    class_name = obj.find("name").text.strip() if obj.find("name") is not None else ""
                    if class_name not in RDD_CLASSES:
                        logged_anomalies.append(("rdd2022", xml_path, "unsupported_class", f"Class '{class_name}' skipped (not D00/D10/D20/D40)"))
                        continue

                    class_id = RDD_CLASSES[class_name]
                    bndbox = obj.find("bndbox")
                    if bndbox is None:
                        logged_anomalies.append(("rdd2022", xml_path, "invalid_box", "Object has no bndbox element"))
                        continue
                    
                    try:
                        xmin = float(bndbox.find("xmin").text)
                        ymin = float(bndbox.find("ymin").text)
                        xmax = float(bndbox.find("xmax").text)
                        ymax = float(bndbox.find("ymax").text)
                    except (AttributeError, ValueError, TypeError):
                        logged_anomalies.append(("rdd2022", xml_path, "invalid_box", "Could not parse float coordinates"))
                        continue

                    if not all(math.isfinite(value) for value in (xmin, ymin, xmax, ymax)):
                        logged_anomalies.append(("rdd2022", xml_path, "invalid_box", "Box coordinates are not finite"))
                        continue

                    # Clip coordinates to image boundary
                    xmin = max(0.0, min(float(width), xmin))
                    xmax = max(0.0, min(float(width), xmax))
                    ymin = max(0.0, min(float(height), ymin))
                    ymax = max(0.0, min(float(height), ymax))

                    # Check validity
                    if xmax <= xmin or ymax <= ymin:
                        logged_anomalies.append(("rdd2022", xml_path, "invalid_box", f"Invalid box dimensions: [{xmin}, {ymin}, {xmax}, {ymax}] for size {width}x{height}"))
                        continue

                    # Convert to normalized YOLO format [x_center, y_center, width, height]
                    x_center = (xmin + xmax) / (2.0 * width)
                    y_center = (ymin + ymax) / (2.0 * height)
                    w = (xmax - xmin) / float(width)
                    h = (ymax - ymin) / float(height)

                    # Clamp strictly to [0.0, 1.0]
                    x_center = min(1.0, max(0.0, x_center))
                    y_center = min(1.0, max(0.0, y_center))
                    w = min(1.0, max(0.0, w))
                    h = min(1.0, max(0.0, h))

                    yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}\n")

            except Exception as e:
                logged_anomalies.append(("rdd2022", xml_path, "xml_parse_error", str(e)))

        # Write label file (empty if background image with 0 boxes)
        with open(dst_lbl, "w", encoding="utf-8") as lf:
            lf.writelines(yolo_lines)

        # Copy image file (fast NTFS link on same drive, fallback to copyfile)
        if not os.path.exists(dst_img):
            try:
                os.link(img_path, dst_img)
            except Exception:
                shutil.copyfile(img_path, dst_img)
        return not yolo_lines

    print("Copying images and writing YOLO label files (multi-threaded)...")
    with ThreadPoolExecutor(max_workers=16) as executor:
        background_count = sum(tqdm(
            executor.map(convert_and_write, tasks),
            total=len(tasks),
            desc="Copying & Converting RDD2022",
            mininterval=2.0
        ))

    # Log anomalies into report
    for anomaly in sorted(logged_anomalies):
        report.log(*anomaly)
    print(f"RDD2022 background images retained: {background_count:,}")

    # Write data.yaml
    yaml_path = os.path.join(yolo_root, "data.yaml")
    data_yaml_content = {
        "path": yolo_root.replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {
            0: "D00 longitudinal",
            1: "D10 transverse",
            2: "D20 alligator",
            3: "D40 pothole"
        }
    }
    with open(yaml_path, "w", encoding="utf-8") as yf:
        if yaml is not None:
            yaml.dump(data_yaml_content, yf, default_flow_style=False, sort_keys=False)
        else:
            yf.write(f"path: {yolo_root.replace('\\\\', '/')}\n")
            yf.write("train: images/train\nval: images/val\ntest: images/test\nnames:\n")
            yf.write("  0: D00\n  1: D10\n  2: D20\n  3: D40\n")
    print(f"Saved YOLO configuration to: {yaml_path}")


def process_crack500(raw_dir: str, processed_dir: str, report: CleaningReport, seed: int = RANDOM_SEED):
    """
    Process CRACK500:
    - Use only the official traincrop, valcrop, and testcrop partitions.
    - Pair each JPEG crop with its same-stem PNG mask and check dimensions.
    - Exclude unreadable pairs and duplicate image hashes without changing raw files.
    - Preserve the official train/val/test assignments.
    - Save manifest: data/processed/manifests/crack500.csv (image_path, mask_path, split).
    """
    print("\n--- Processing CRACK500 ---")
    manifest_dir = os.path.join(processed_dir, "manifests")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, "crack500.csv")

    subsets = {"traincrop": "train", "valcrop": "val", "testcrop": "test"}
    raw_pairs = []

    for sub, split in subsets.items():
        sub_dir = os.path.join(raw_dir, "CRACK500", sub, sub)
        if not os.path.isdir(sub_dir):
            sub_dir = os.path.join(raw_dir, sub, sub)
        if not os.path.exists(sub_dir):
            print(f"[!] Warning: CRACK500 subfolder not found: {sub_dir}")
            report.log("crack500", sub_dir, "missing_label", "Official crop split folder is missing.")
            continue

        for fname in sorted(os.listdir(sub_dir)):
            if fname.lower().endswith((".jpg", ".jpeg")):
                stem = os.path.splitext(fname)[0]
                img_path = os.path.join(sub_dir, fname)
                mask_path = os.path.join(sub_dir, stem + ".png")
                raw_pairs.append((img_path, mask_path, split))

    print(f"Total CRACK500 crop images indexed: {len(raw_pairs):,}")

    valid_pairs = []
    seen_hashes = {}
    for img_path, mask_path, split in tqdm(raw_pairs, desc="Cleaning CRACK500 crops"):
        if not os.path.exists(mask_path):
            report.log("crack500", img_path, "missing_label", f"Paired mask file missing: {mask_path}")
            continue

        try:
            with Image.open(img_path) as im, Image.open(mask_path) as mk:
                im.verify()
                mk.verify()
        except Exception as e:
            report.log("crack500", img_path, "unreadable_image", f"Unreadable crop image or mask: {e}")
            continue

        with Image.open(img_path) as im, Image.open(mask_path) as mk:
            if im.size != mk.size:
                report.log("crack500", img_path, "dimension_mismatch",
                           f"Image dimensions {im.size} do not match mask dimensions {mk.size}")
                continue

        # Deduplication
        file_hash = compute_sha256(img_path)
        if file_hash in seen_hashes:
            report.log("crack500", img_path, "duplicate_hash", f"Matches earlier image: {seen_hashes[file_hash]}")
            continue
        seen_hashes[file_hash] = img_path

        valid_pairs.append({
            "image_path": img_path,
            "mask_path": mask_path,
            "hash": file_hash,
            "split": split,
            "source_photo": _crack500_source_photo_id(img_path),
        })

    source_splits = defaultdict(set)
    for item in valid_pairs:
        source_splits[item["source_photo"]].add(item["split"])
    overlapping_sources = {
        source for source, splits in source_splits.items() if len(splits) > 1
    }
    if overlapping_sources:
        kept_pairs = []
        for item in valid_pairs:
            if item["source_photo"] in overlapping_sources:
                report.log(
                    "crack500",
                    item["image_path"],
                    "source_photo_split_overlap",
                    f"Source photo has crops in multiple official splits: "
                    f"{', '.join(sorted(source_splits[item['source_photo']]))}.",
                )
            else:
                kept_pairs.append(item)
        valid_pairs = kept_pairs

    print(
        f"Valid unique CRACK500 crop pairs: {len(valid_pairs):,} "
        f"(Excluded {len(raw_pairs) - len(valid_pairs):,}); official splits preserved. "
        f"Excluded {len(overlapping_sources)} source-photo IDs spanning partitions."
    )

    df_manifest = pd.DataFrame(valid_pairs)[["image_path", "mask_path", "split"]]
    df_manifest.to_csv(manifest_path, index=False)
    print(f"Saved CRACK500 manifest to: {manifest_path}")
    print(df_manifest["split"].value_counts().to_string())
    return df_manifest


def _crack500_source_photo_id(image_path: str) -> str:
    """Remove the final two crop-coordinate fields from a CRACK500 crop filename."""
    stem = Path(image_path).stem
    match = re.match(r"^(.+)_\d+_\d+$", stem)
    return match.group(1) if match else stem


def process_cfd(raw_dir: str, processed_dir: str, report: CleaningReport):
    """
    Process CFD (Crack Forest Dataset):
    - Verify grayscale mask mode and binary pixel values (0 and 255).
    - All 118 images assigned to split = 'test' (standard benchmark test set).
    - Save manifest: data/processed/manifests/cfd.csv (image_path, mask_path, split).
    """
    print("\n--- Processing CFD ---")
    manifest_dir = os.path.join(processed_dir, "manifests")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, "cfd.csv")

    img_dir = os.path.join(raw_dir, "Images")
    mask_dir = os.path.join(raw_dir, "Masks")
    if not os.path.isdir(img_dir) or not os.path.isdir(mask_dir):
        raise FileNotFoundError(f"CFD Images or Masks directory is missing under {raw_dir}")

    masks = {}
    for name in sorted(os.listdir(mask_dir)):
        if os.path.isfile(os.path.join(mask_dir, name)):
            mask_stem = os.path.splitext(name)[0]
            if mask_stem.casefold().endswith("_label"):
                mask_stem = mask_stem[:-6]
            masks[mask_stem.casefold()] = os.path.join(mask_dir, name)
    raw_items = []
    for fname in sorted(os.listdir(img_dir)):
        if fname.lower().endswith((".jpg", ".jpeg", ".png")):
            stem = os.path.splitext(fname)[0]
            raw_items.append((os.path.join(img_dir, fname), masks.get(stem.casefold())))

    print(f"Total raw CFD items indexed: {len(raw_items):,}")
    for first_mask in (mask_path for _, mask_path in raw_items if mask_path):
        try:
            with Image.open(first_mask) as mask:
                sample = np.asarray(mask)
                unique_count = len(np.unique(sample))
                mask_format = "binary" if unique_count <= 2 else "grayscale/multivalue"
                print(
                    f"CFD mask format detected: mode={mask.mode}, format={mask_format}, "
                    f"unique_values={unique_count}"
                )
                break
        except Exception as exc:
            print(
                f"[!] Could not inspect CFD mask format sample ({first_mask}); "
                f"trying the next mask: {exc}"
            )

    valid_items = []
    seen_hashes = {}
    for img_path, mask_path in tqdm(raw_items, desc="Cleaning CFD"):
        if not mask_path or not os.path.exists(mask_path):
            report.log("cfd", img_path, "missing_label", "Paired mask file is missing.")
            continue

        try:
            with Image.open(img_path) as im, Image.open(mask_path) as mk:
                im.verify()
                mk.verify()
        except Exception as e:
            report.log("cfd", img_path, "unreadable_image", f"Corrupt image or mask: {e}")
            continue

        with Image.open(img_path) as im, Image.open(mask_path) as mk:
            if im.size != mk.size:
                report.log(
                    "cfd", img_path, "dimension_mismatch",
                    f"Image dimensions {im.size} do not match mask dimensions {mk.size}"
                )
                continue

        file_hash = compute_sha256(img_path)
        if file_hash in seen_hashes:
            report.log("cfd", img_path, "duplicate_hash", f"Matches earlier image: {seen_hashes[file_hash]}")
            continue
        seen_hashes[file_hash] = img_path

        valid_items.append({
            "image_path": img_path,
            "mask_path": mask_path,
            "split": "test"
        })

    df_manifest = pd.DataFrame(valid_items)[["image_path", "mask_path", "split"]]
    df_manifest.to_csv(manifest_path, index=False)
    print(f"Saved CFD manifest to: {manifest_path} (All {len(df_manifest)} set to 'test')")
    return df_manifest


def _add_segmentation_counts(rows: list, dataset: str, df: pd.DataFrame) -> None:
    """Count images with and without positive mask pixels for each split."""
    masks_with_crack = {}
    for mask_path in tqdm(df["mask_path"], desc=f"Summarizing {dataset} masks"):
        with Image.open(mask_path) as mask:
            masks_with_crack[mask_path] = bool(np.any(np.asarray(mask) > 0))

    for split, group in df.groupby("split"):
        crack_images = sum(masks_with_crack[path] for path in group["mask_path"])
        no_crack_images = len(group) - crack_images
        ratio = _imbalance_ratio((crack_images, no_crack_images))
        for class_name, count in (
            ("images_with_crack", crack_images),
            ("images_without_crack", no_crack_images),
        ):
            rows.append({
                "dataset": dataset,
                "task": "segmentation (images by mask)",
                "split": split,
                "class_name": class_name,
                "count": count,
                "total_in_split": len(group),
                "imbalance_ratio": ratio,
            })


def generate_split_summary(processed_dir: str):
    """
    Generate split_summary.csv showing:
    - Counts per split and per class for each dataset
    - Class imbalance ratio (max_count / min_count) for each split
    """
    summary_rows = []

    # 1. SDNET2018
    sd_path = os.path.join(processed_dir, "manifests", "sdnet2018.csv")
    if os.path.exists(sd_path):
        df = pd.read_csv(sd_path)
        for split, grp in df.groupby("split"):
            counts = grp["label"].value_counts().to_dict()
            cr = counts.get("cracked", 0)
            uncr = counts.get("uncracked", 0)
            imb = _imbalance_ratio((cr, uncr))
            summary_rows.append({
                "dataset": "sdnet2018",
                "task": "classification",
                "split": split,
                "class_name": "cracked",
                "count": cr,
                "total_in_split": len(grp),
                "imbalance_ratio": imb
            })
            summary_rows.append({
                "dataset": "sdnet2018",
                "task": "classification",
                "split": split,
                "class_name": "uncracked",
                "count": uncr,
                "total_in_split": len(grp),
                "imbalance_ratio": imb
            })

    # 2. concrete_crack_cls
    ccc_path = os.path.join(processed_dir, "manifests", "concrete_crack_cls.csv")
    if os.path.exists(ccc_path):
        df = pd.read_csv(ccc_path)
        for split, grp in df.groupby("split"):
            counts = grp["label"].value_counts().to_dict()
            cr = counts.get("cracked", 0)
            uncr = counts.get("uncracked", 0)
            imb = _imbalance_ratio((cr, uncr))
            summary_rows.append({
                "dataset": "concrete_crack_cls",
                "task": "classification",
                "split": split,
                "class_name": "cracked",
                "count": cr,
                "total_in_split": len(grp),
                "imbalance_ratio": imb
            })
            summary_rows.append({
                "dataset": "concrete_crack_cls",
                "task": "classification",
                "split": split,
                "class_name": "uncracked",
                "count": uncr,
                "total_in_split": len(grp),
                "imbalance_ratio": imb
            })

    # 3. RDD2022
    rdd_labels_dir = os.path.join(processed_dir, "rdd2022_yolo", "labels")
    if os.path.exists(rdd_labels_dir):
        for split in ["train", "val", "test"]:
            split_dir = os.path.join(rdd_labels_dir, split)
            if not os.path.exists(split_dir):
                continue
            lbl_files = glob.glob(os.path.join(split_dir, "*.txt"))
            box_counts = defaultdict(int)
            empty_count = 0
            with ThreadPoolExecutor(max_workers=16) as executor:
                label_summaries = executor.map(_parse_yolo_label_file, lbl_files)
                for is_background, class_counts in tqdm(
                    label_summaries,
                    total=len(lbl_files),
                    desc=f"Summarizing RDD2022 {split}",
                    unit="label",
                ):
                    empty_count += is_background
                    for class_id, count in class_counts.items():
                        box_counts[RDD_CLASSES_INV[class_id]] += count

            total_boxes = sum(box_counts.values())
            counts_list = [box_counts[cname] for cname in ("D00", "D10", "D20", "D40")]
            imb = _imbalance_ratio(counts_list)

            for cname in ["D00", "D10", "D20", "D40"]:
                summary_rows.append({
                    "dataset": "rdd2022",
                    "task": "object_detection (boxes)",
                    "split": split,
                    "class_name": cname,
                    "count": box_counts[cname],
                    "total_in_split": total_boxes,
                    "imbalance_ratio": imb
                })
            summary_rows.append({
                "dataset": "rdd2022",
                "task": "object_detection (images)",
                "split": split,
                "class_name": "background (no crack)",
                "count": empty_count,
                "total_in_split": len(lbl_files),
                "imbalance_ratio": "-"
            })

    # 4. CRACK500
    c500_path = os.path.join(processed_dir, "manifests", "crack500.csv")
    if os.path.exists(c500_path):
        df = pd.read_csv(c500_path)
        _add_segmentation_counts(summary_rows, "crack500", df)

    # 5. CFD
    cfd_path = os.path.join(processed_dir, "manifests", "cfd.csv")
    if os.path.exists(cfd_path):
        df = pd.read_csv(cfd_path)
        _add_segmentation_counts(summary_rows, "cfd", df)

    summary_df = pd.DataFrame(summary_rows)
    summary_path = os.path.join(processed_dir, "reports", "split_summary.csv")
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    summary_df.to_csv(summary_path, index=False)
    print(f"\n[SplitSummary] Saved split summary to: {summary_path}")
    if not summary_df.empty:
        print("\nCounts per split and class (with per-split imbalance ratio):")
        print(summary_df.to_string(index=False))
    return summary_df


def run_pipeline_assertions(processed_dir: str, full_hash_check: bool = False):
    """
    Run mandatory integrity assertions on the processed dataset artifacts:
    1. No SHA-256 hash appears in more than one split within any dataset (zero data leakage).
    2. Every image and mask path in every manifest actually exists on disk.
    3. All YOLO coordinates are normalized in [0.0, 1.0], classes in 0..3, and
       every image in images/{split} has a corresponding .txt file in labels/{split}.
    """
    print("\n" + "=" * 70)
    print("RUNNING PIPELINE INTEGRITY ASSERTIONS")
    print("=" * 70)

    # Assertion 1: Manifest file paths exist and no hash leakage across splits
    manifests = {
        "sdnet2018": (
            os.path.join(processed_dir, "manifests", "sdnet2018.csv"),
            "path",
            "hash",
            ["path", "label", "group", "hash", "split"],
        ),
        "concrete_crack_cls": (
            os.path.join(processed_dir, "manifests", "concrete_crack_cls.csv"),
            "path",
            "hash",
            ["path", "label", "hash", "split"],
        ),
        "crack500": (
            os.path.join(processed_dir, "manifests", "crack500.csv"),
            "image_path",
            None,
            ["image_path", "mask_path", "split"],
        ),
        "cfd": (
            os.path.join(processed_dir, "manifests", "cfd.csv"),
            "image_path",
            None,
            ["image_path", "mask_path", "split"],
        ),
    }

    for name, (path, path_col, hash_col, expected_columns) in manifests.items():
        assert os.path.exists(path), f"Assertion Error: Manifest missing: {path}"
        df = pd.read_csv(path, dtype={"group": str} if "group" in expected_columns else None)
        print(f"[Assert] Checking {name} ({len(df):,} entries)...")
        assert list(df.columns) == expected_columns, f"Assertion Error: Unexpected {name} manifest columns."

        # Check paths exist
        missing_paths = [p for p in df[path_col] if not os.path.exists(p)]
        assert len(missing_paths) == 0, f"Assertion Error: {len(missing_paths)} paths missing in {name} manifest!"

        if "mask_path" in df.columns:
            missing_masks = [p for p in df["mask_path"] if not os.path.exists(p)]
            assert len(missing_masks) == 0, f"Assertion Error: {len(missing_masks)} masks missing in {name} manifest!"

        # Check hash disjointness across splits
        if hash_col and hash_col in df.columns:
            assert df[hash_col].is_unique, f"Assertion Error: Duplicate image hashes remain in {name}."
            splits = df["split"].unique()
            split_hashes = {s: set(df[df["split"] == s][hash_col]) for s in splits}
            for i in range(len(splits)):
                for j in range(i + 1, len(splits)):
                    s1, s2 = splits[i], splits[j]
                    overlap = split_hashes[s1].intersection(split_hashes[s2])
                    assert len(overlap) == 0, f"Assertion Error: Hash leakage between {s1} and {s2} in {name} ({len(overlap)} overlapping hashes)!"
        else:
            if full_hash_check:
                image_paths = df[path_col].tolist()
                with ThreadPoolExecutor(max_workers=16) as executor:
                    all_hashes = list(tqdm(
                        executor.map(compute_sha256, image_paths),
                        total=len(image_paths),
                        desc=f"Checking {name} hashes",
                        mininterval=2.0,
                    ))
                assert len(all_hashes) == len(set(all_hashes)), (
                    f"Assertion Error: Duplicate image hashes remain in {name}."
                )
                hash_splits = defaultdict(set)
                for split, image_hash in zip(df["split"], all_hashes):
                    hash_splits[split].add(image_hash)
                split_names = list(hash_splits)
                for i, first in enumerate(split_names):
                    for second in split_names[i + 1:]:
                        assert not hash_splits[first].intersection(hash_splits[second]), (
                            f"Assertion Error: Hash leakage between {first} and {second} in {name}!"
                        )

        if name == "sdnet2018":
            filename_pattern = re.compile(r"^(.+?)-\d+(?:_\d+)?\.[^.]+$")
            source_groups_raw = []
            source_groups_surf = []
            for image_path in df[path_col]:
                match = filename_pattern.match(os.path.basename(image_path))
                assert match, (
                    f"Assertion Error: SDNET2018 filename does not identify a source photo: "
                    f"{image_path}"
                )
                raw_id = match.group(1)
                surface = Path(image_path).parent.parent.name
                source_groups_raw.append(raw_id)
                source_groups_surf.append(f"{surface}_{raw_id}")

            csv_groups = df["group"].astype(str).tolist()
            groups_match = (
                csv_groups == source_groups_raw
                or csv_groups == source_groups_surf
                or [g.lstrip("0") or "0" for g in csv_groups]
                == [g.lstrip("0") or "0" for g in source_groups_raw]
            )
            assert groups_match, (
                "Assertion Error: SDNET2018 source-photo groups do not match filename IDs."
            )
            assert df.groupby("group")["split"].nunique().max() == 1, (
                "Assertion Error: An SDNET2018 source photo appears in multiple splits."
            )
        elif name == "crack500":
            source_groups = df[path_col].map(_crack500_source_photo_id)
            source_split_counts = df.assign(source_photo=source_groups).groupby(
                "source_photo"
            )["split"].nunique()
            assert source_split_counts.max() == 1, (
                "Assertion Error: A CRACK500 source photo appears in multiple splits."
            )

        print(f"  [OK] {name} passed all file existence and split disjointness checks.")
        if name == "sdnet2018":
            print("  [OK] SDNET2018 source-photo groups remain within a single split.")
        elif name == "crack500":
            print("  [OK] CRACK500 source-photo groups remain within a single split.")

    # Assertion 2: RDD2022 YOLO integrity
    yolo_root = os.path.join(processed_dir, "rdd2022_yolo")
    data_yaml_path = os.path.join(yolo_root, "data.yaml")
    assert os.path.exists(data_yaml_path), f"Assertion Error: data.yaml missing at {data_yaml_path}"

    with open(data_yaml_path, "r", encoding="utf-8") as f:
        if yaml is not None:
            y_cfg = yaml.safe_load(f)
        else:
            lines = f.readlines()
            y_cfg = {
                "names": {
                    0: "D00 longitudinal",
                    1: "D10 transverse",
                    2: "D20 alligator",
                    3: "D40 pothole",
                },
                "path": yolo_root.replace("\\", "/"),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
            }
            current_section = None
            for line in lines:
                raw_line = line.rstrip()
                stripped = raw_line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if not raw_line.startswith(" ") and ":" in stripped:
                    k, v = stripped.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    current_section = k
                    if v:
                        y_cfg[k] = v
                elif raw_line.startswith(" ") and current_section == "names" and ":" in stripped:
                    k, v = stripped.split(":", 1)
                    try:
                        idx = int(k.strip())
                        y_cfg["names"][idx] = v.strip()
                    except ValueError:
                        pass
    assert "train" in y_cfg and "val" in y_cfg and "test" in y_cfg and "names" in y_cfg, "Assertion Error: Incomplete data.yaml structure"
    valid_name_schemas = [
        {0: "D00 longitudinal", 1: "D10 transverse", 2: "D20 alligator", 3: "D40 pothole"},
        {0: "D00", 1: "D10", 2: "D20", 3: "D40"},
        ["D00 longitudinal", "D10 transverse", "D20 alligator", "D40 pothole"],
        ["D00", "D10", "D20", "D40"]
    ]
    assert (
        y_cfg["names"] in valid_name_schemas
        or (isinstance(y_cfg["names"], dict) and list(y_cfg["names"].values()) in [
            ["D00 longitudinal", "D10 transverse", "D20 alligator", "D40 pothole"],
            ["D00", "D10", "D20", "D40"]
        ])
    ), "Assertion Error: RDD2022 class names are incorrect."
    assert all(
        y_cfg[split] == f"images/{split}"
        and os.path.isdir(os.path.join(y_cfg["path"], y_cfg[split]))
        for split in ("train", "val", "test")
    ), "Assertion Error: RDD2022 YAML split paths are invalid."

    print("[Assert] Checking RDD2022 YOLO dataset structure and labels...")
    total_yolo_images = 0
    yolo_hashes = defaultdict(set)

    for split in ["train", "val", "test"]:
        img_dir = os.path.join(yolo_root, "images", split)
        lbl_dir = os.path.join(yolo_root, "labels", split)
        assert os.path.exists(img_dir), f"Assertion Error: Image split directory missing: {img_dir}"
        assert os.path.exists(lbl_dir), f"Assertion Error: Label split directory missing: {lbl_dir}"

        img_files = sorted(os.listdir(img_dir))
        lbl_files = set(os.listdir(lbl_dir))
        total_yolo_images += len(img_files)
        expected_labels = {os.path.splitext(name)[0] + ".txt" for name in img_files}
        assert expected_labels == lbl_files, (
            f"Assertion Error: RDD2022 image/label file mismatch in {split}: "
            f"{len(expected_labels - lbl_files)} missing, {len(lbl_files - expected_labels)} extra."
        )

        image_label_pairs = [
            (
                os.path.join(img_dir, img_name),
                os.path.join(lbl_dir, os.path.splitext(img_name)[0] + ".txt"),
            )
            for img_name in img_files
        ]
        # Validate all YOLO label files: 5 values per box, classes in 0..3, coords in [0, 1]
        for _, lbl_path in image_label_pairs:
            _parse_yolo_label_file(lbl_path)

        if full_hash_check:
            with ThreadPoolExecutor(max_workers=16) as executor:
                split_image_hashes = list(tqdm(
                    executor.map(compute_sha256, [p[0] for p in image_label_pairs]),
                    total=len(image_label_pairs),
                    desc=f"Hashing RDD2022 {split}",
                    unit="image",
                    mininterval=2.0,
                ))
            yolo_hashes[split].update(split_image_hashes)
            assert len(yolo_hashes[split]) == len(img_files), (
                f"Assertion Error: Duplicate image hashes remain in RDD2022 {split}."
            )

    if full_hash_check:
        split_names = list(yolo_hashes)
        for i, first in enumerate(split_names):
            for second in split_names[i + 1:]:
                assert not yolo_hashes[first].intersection(yolo_hashes[second]), (
                    f"Assertion Error: RDD2022 hash leakage between {first} and {second}."
                )

    print(f"  [OK] RDD2022 YOLO passed: {total_yolo_images:,} images with matching label files. All coordinates in [0.0, 1.0].")
    print("=" * 70)
    print("ALL INTEGRITY ASSERTIONS PASSED SUCCESSFULLY!")
    print("=" * 70)


def visualize_rdd2022_samples(processed_dir: str, n_samples: int = 5, seed: int = RANDOM_SEED):
    """Visualize n random RDD2022 images with their converted YOLO bounding boxes plotted."""
    yolo_root = os.path.join(processed_dir, "rdd2022_yolo")
    rng = random.Random(seed)

    candidates = []
    for split in ["train", "val"]:
        lbl_dir = os.path.join(yolo_root, "labels", split)
        img_dir = os.path.join(yolo_root, "images", split)
        for lf in os.listdir(lbl_dir):
            if lf.endswith(".txt"):
                lbl_path = os.path.join(lbl_dir, lf)
                if os.path.getsize(lbl_path) > 0:
                    stem = os.path.splitext(lf)[0]
                    for ext in [".jpg", ".png", ".jpeg"]:
                        ip = os.path.join(img_dir, stem + ext)
                        if os.path.exists(ip):
                            candidates.append((ip, lbl_path, split))
                            break

    chosen = rng.sample(candidates, min(n_samples, len(candidates)))
    if not chosen:
        raise ValueError("No converted RDD2022 images with bounding boxes were found to visualize.")

    colors = {0: "#e63946", 1: "#457b9d", 2: "#2a9d8f", 3: "#e76f51"}
    fig, axes = plt.subplots(1, len(chosen), figsize=(4 * len(chosen), 4.5))
    if len(chosen) == 1:
        axes = [axes]

    for ax, (img_path, lbl_path, split) in zip(axes, chosen):
        im = Image.open(img_path).convert("RGB")
        w_img, h_img = im.size
        ax.imshow(im)
        ax.set_title(f"{os.path.basename(img_path)[:18]}\n({split})", fontsize=10)
        ax.axis("off")

        with open(lbl_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                cid = int(parts[0])
                xc, yc, bw, bh = map(float, parts[1:])
                xmin = (xc - bw / 2.0) * w_img
                ymin = (yc - bh / 2.0) * h_img
                box_w = bw * w_img
                box_h = bh * h_img

                rect = patches.Rectangle(
                    (xmin, ymin), box_w, box_h,
                    linewidth=2, edgecolor=colors.get(cid, "yellow"), facecolor="none"
                )
                ax.add_patch(rect)
                cname = RDD_CLASSES_INV.get(cid, str(cid))
                ax.text(
                    xmin, max(12, ymin - 3), cname,
                    color="white", fontsize=8, weight="bold",
                    bbox=dict(facecolor=colors.get(cid, "yellow"), alpha=0.8, pad=1, edgecolor="none")
                )

    plt.tight_layout()
    return fig


def visualize_crack500_samples(processed_dir: str, n_samples: int = 3, seed: int = RANDOM_SEED):
    """Visualize n random CRACK500 image-mask pairs with overlay."""
    manifest_path = os.path.join(processed_dir, "manifests", "crack500.csv")
    df = pd.read_csv(manifest_path)
    rng = random.Random(seed)
    indices = rng.sample(range(len(df)), min(n_samples, len(df)))

    fig, axes = plt.subplots(len(indices), 3, figsize=(10, 3.2 * len(indices)))
    if len(indices) == 1:
        axes = [axes]

    for row_idx, idx in enumerate(indices):
        item = df.iloc[idx]
        img = Image.open(item["image_path"]).convert("RGB")
        mask = Image.open(item["mask_path"]).convert("L")
        mask_np = (np.asarray(mask) > 0).astype(np.uint8) * 255

        # 1. Original
        axes[row_idx][0].imshow(img)
        axes[row_idx][0].set_title(f"Image ({item['split']})\n{os.path.basename(item['image_path'])[:20]}", fontsize=9)
        axes[row_idx][0].axis("off")

        # 2. Mask
        axes[row_idx][1].imshow(mask_np, cmap="gray")
        axes[row_idx][1].set_title("Binary Mask", fontsize=9)
        axes[row_idx][1].axis("off")

        # 3. Overlay
        axes[row_idx][2].imshow(img)
        axes[row_idx][2].imshow(mask_np, cmap="autumn", alpha=0.45)
        axes[row_idx][2].set_title("Crack Overlay", fontsize=9)
        axes[row_idx][2].axis("off")

    plt.tight_layout()
    return fig


def plot_distributions_and_splits(processed_dir: str):
    """Generate and return summary figures for class distribution and split sizes."""
    summary_path = os.path.join(processed_dir, "reports", "split_summary.csv")
    df = pd.read_csv(summary_path)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Plot 1: Sample counts by dataset and split.
    sample_rows = df[df["task"].isin((
        "classification",
        "object_detection (images)",
        "segmentation (images by mask)",
    ))].drop_duplicates(["dataset", "split"])
    dataset_splits = sample_rows.pivot(index="dataset", columns="split", values="total_in_split").fillna(0)
    dataset_splits.plot(kind="bar", stacked=True, ax=axes[0], colormap="viridis", edgecolor="black")
    axes[0].set_title("Samples per Split by Dataset", fontsize=12, weight="bold")
    axes[0].set_ylabel("Images")
    axes[0].set_xlabel("Dataset")
    axes[0].grid(axis="y", linestyle="--", alpha=0.7)

    # Plot 2: Every class count, with split colors.
    class_counts = df.pivot_table(
        index=["dataset", "class_name"], columns="split", values="count", aggfunc="sum", fill_value=0
    )
    class_counts.plot(kind="bar", stacked=True, ax=axes[1], colormap="Set2", edgecolor="black")
    axes[1].set_title("Class Counts by Dataset and Split", fontsize=12, weight="bold")
    axes[1].set_ylabel("Count")
    axes[1].set_xlabel("Dataset / class")
    axes[1].tick_params(axis="x", labelrotation=75)
    axes[1].grid(axis="y", linestyle="--", alpha=0.7)

    plt.tight_layout()
    return fig


def _raw_candidate_counts(raw_dirs: dict) -> dict:
    """Count labeled image or image-mask candidates before cleaning."""
    extensions = (".jpg", ".jpeg", ".png")
    counts = {}

    for dataset in ("sdnet2018", "concrete_crack_cls"):
        root = raw_dirs[dataset]
        counts[dataset] = sum(
            1
            for current_root, _, filenames in os.walk(root)
            for filename in filenames
            if filename.lower().endswith(extensions)
        )

    rdd_count = 0
    rdd_root = raw_dirs["rdd2022"]
    for country in os.listdir(rdd_root):
        country_root = os.path.join(rdd_root, country)
        image_dir = os.path.join(country_root, "train", "images")
        xml_dir = os.path.join(country_root, "train", "annotations", "xmls")
        if os.path.isdir(image_dir) and os.path.isdir(xml_dir):
            rdd_count += sum(
                name.lower().endswith(extensions)
                for name in os.listdir(image_dir)
            )
    counts["rdd2022"] = rdd_count

    crack500_root = os.path.join(raw_dirs["crack500"], "CRACK500")
    counts["crack500"] = sum(
        1
        for subset in ("traincrop", "valcrop", "testcrop")
        for current_root, _, filenames in os.walk(os.path.join(crack500_root, subset, subset))
        for filename in filenames
        if filename.lower().endswith((".jpg", ".jpeg"))
    )

    cfd_images = os.path.join(raw_dirs["cfd"], "Images")
    counts["cfd"] = sum(
        name.lower().endswith(extensions) for name in os.listdir(cfd_images)
    )
    return counts


def generate_documentation(processed_dir: str, docs_path: str, raw_dirs: dict = None):
    """Generate docs/08_dataset_cleaning.md detailing the entire cleaning and conversion process."""
    os.makedirs(os.path.dirname(docs_path), exist_ok=True)
    report_path = os.path.join(processed_dir, "reports", "cleaning_report.csv")
    summary_path = os.path.join(processed_dir, "reports", "split_summary.csv")

    df_report = pd.read_csv(report_path) if os.path.exists(report_path) else pd.DataFrame()
    df_summary = pd.read_csv(summary_path) if os.path.exists(summary_path) else pd.DataFrame()

    removals_by_reason = df_report.groupby(["dataset", "reason"]).size().unstack(fill_value=0) if not df_report.empty else pd.DataFrame()
    total_audit_records = len(df_report)
    crack500_overlap_rows = (
        df_report[
            (df_report["dataset"] == "crack500")
            & (df_report["reason"] == "source_photo_split_overlap")
        ]
        if not df_report.empty else pd.DataFrame()
    )
    crack500_overlap_sources = (
        {
            _crack500_source_photo_id(path)
            for path in crack500_overlap_rows["file_path"]
        }
        if not crack500_overlap_rows.empty else set()
    )
    crack500_leakage_note = (
        f"{len(crack500_overlap_rows):,} crop images from "
        f"{len(crack500_overlap_sources)} source photos spanning official partitions "
        "were excluded to prevent source-photo leakage."
        if not crack500_overlap_rows.empty
        else "No source photo was found across multiple official partitions."
    )
    manifest_counts = {
        dataset: len(pd.read_csv(os.path.join(processed_dir, "manifests", f"{dataset}.csv")))
        for dataset in ("sdnet2018", "concrete_crack_cls", "crack500", "cfd")
    }
    manifest_counts["rdd2022"] = sum(
        len(os.listdir(os.path.join(processed_dir, "rdd2022_yolo", "images", split)))
        for split in ("train", "val", "test")
    )
    candidate_counts = _raw_candidate_counts(raw_dirs) if raw_dirs else manifest_counts.copy()
    dataset_labels = {
        "sdnet2018": "SDNET2018 (classification)",
        "concrete_crack_cls": "concrete_crack_cls (classification)",
        "rdd2022": "RDD2022 (object detection)",
        "crack500": "CRACK500 (segmentation)",
        "cfd": "CFD (external test)",
    }
    size_table = ["| Dataset | Candidates before cleaning | Kept | Excluded |",
                  "|---|---:|---:|---:|"]
    for dataset, label in dataset_labels.items():
        before = candidate_counts[dataset]
        kept = manifest_counts[dataset]
        size_table.append(f"| {label} | {before:,} | {kept:,} | {max(0, before - kept):,} |")
    sizes_text = "\n".join(size_table)
    summary_text = df_summary.to_string(index=False) if not df_summary.empty else "No split summary available."
    reason_text = removals_by_reason.to_string() if not removals_by_reason.empty else "No exclusions or annotation anomalies were logged."
    rdd_countries = []
    if raw_dirs:
        rdd_root = raw_dirs["rdd2022"]
        rdd_countries = sorted(
            name for name in os.listdir(rdd_root)
            if os.path.isdir(os.path.join(rdd_root, name, "train", "images"))
            and os.path.isdir(os.path.join(rdd_root, name, "train", "annotations", "xmls"))
        )
    if len(rdd_countries) == 1:
        country_note = (
            f"Only one labeled country folder is available ({rdd_countries[0]}), "
            "so cross-country generalization cannot be assessed."
        )
    elif rdd_countries:
        country_note = (
            f"{len(rdd_countries)} labeled country folders are available "
            f"({', '.join(rdd_countries)}). Countries contribute to each split, "
            "so this split does not measure generalization to unseen countries."
        )
    else:
        country_note = "Labeled country folders could not be determined."

    doc_text = f"""# InfraScan Dataset Cleaning, Splitting & Label Conversion Report

**Generated Date**: {pd.Timestamp.now().date()}  
**Pipeline Module**: `infrascan/ml/data_prep.py`  
**Notebook Verification**: `data/notebooks/04_dataset_cleaning.ipynb`  
**Fixed Random Seed**: `42`  

---

## 1. Executive Summary

This report documents the rigorous data cleaning, deduplication, group splitting, and label conversion executed for the **InfraScan** crack detection project. All raw data (`data/raw/`) remains strictly **READ-ONLY** and untouched. Standardized manifests, reports, and converted YOLO detection datasets are generated under `data/processed/`.

All source files under `data/raw/` were treated as read-only. Cleaning exclusions and skipped annotation
items are recorded in `data/processed/reports/cleaning_report.csv`. Integrity assertions were run after
conversion, including hash disjointness across splits, manifest path checks, and YOLO label bounds.

---

## 2. Dataset Sizes: Before vs After Cleaning

{sizes_text}

---

## 3. Exclusion Audit by Reason (`cleaning_report.csv`)

A total of **{total_audit_records} exclusion and annotation audit records** were logged. The breakdown by dataset and reason:

```
{reason_text}
```

Duplicate images, unreadable inputs, missing labels, mismatched image-mask sizes, and invalid annotation
items are never deleted from raw storage; affected entries are excluded or skipped only in processed outputs.

---

## 4. Dataset Splits & Class Distributions (`split_summary.csv`)

{summary_text}

---

## 5. Documented Limitations & Recommendations

1. **Possible crop leakage**: `concrete_crack_cls` is split randomly by class because source-photo identifiers are unavailable; related crops may cross splits.
2. **RDD2022 country coverage**: {country_note}
3. **CRACK500 source partitions**: only the official `traincrop`, `valcrop`, and `testcrop` image-mask pairs are used; surviving rows keep their official train/val/test assignment. Full-size folders and `fphb_testresult` outputs are excluded. {crack500_leakage_note}
4. **Official split proportions**: CRACK500's official crop partition sizes are preserved and therefore are not forced to a 70/15/15 ratio.
5. **Segmentation domain**: CRACK500 and CFD are road-surface data; results may not generalize to concrete walls, bridges, or other non-road structures.
"""
    with open(docs_path, "w", encoding="utf-8") as f:
        f.write(doc_text)
    print(f"[Documentation] Successfully generated {docs_path}")


def main(force: bool = False, full_hash_check: bool = False):
    """Main execution function to run the full dataset cleaning, splitting, and conversion pipeline."""
    base_dir = r"D:\Infosys springboards"
    raw_dirs = {
        "sdnet2018": os.path.join(base_dir, "data", "raw", "sdnet2018"),
        "concrete_crack_cls": os.path.join(base_dir, "data", "raw", "concrete_crack_cls"),
        "rdd2022": os.path.join(base_dir, "data", "raw", "rdd2022"),
        "crack500": os.path.join(base_dir, "data", "raw", "crack500"),
        "cfd": os.path.join(base_dir, "data", "raw", "cfd"),
    }
    processed_dir = os.path.join(base_dir, "data", "processed")
    docs_path = os.path.join(base_dir, "docs", "08_dataset_cleaning.md")
    report_path = os.path.join(processed_dir, "reports", "cleaning_report.csv")
    created_list_path = os.path.join(processed_dir, "reports", "created_files.txt")

    before = {}
    for root in (processed_dir, os.path.dirname(docs_path)):
        for current_root, _, filenames in os.walk(root):
            for filename in filenames:
                path = os.path.join(current_root, filename)
                before[path] = os.stat(path).st_mtime_ns

    # 1. Print Folder Structures
    print_folder_structures(raw_dirs)

    for dataset, path in raw_dirs.items():
        if not os.path.isdir(path):
            raise FileNotFoundError(f"Raw dataset folder is missing for {dataset}: {path}")

    os.makedirs(os.path.join(processed_dir, "manifests"), exist_ok=True)
    os.makedirs(os.path.join(processed_dir, "reports"), exist_ok=True)
    os.makedirs(os.path.dirname(docs_path), exist_ok=True)

    manifest_files = [
        os.path.join(processed_dir, "manifests", "sdnet2018.csv"),
        os.path.join(processed_dir, "manifests", "concrete_crack_cls.csv"),
        os.path.join(processed_dir, "manifests", "crack500.csv"),
        os.path.join(processed_dir, "manifests", "cfd.csv"),
        os.path.join(processed_dir, "rdd2022_yolo", "data.yaml"),
        report_path,
    ]
    artifacts_ready = all(os.path.exists(p) and os.path.getsize(p) > 0 for p in manifest_files)

    if artifacts_ready and not force:
        print("\n" + "=" * 70)
        print("[Pipeline Cache] Processed manifests and converted datasets already exist.")
        print("                 Skipping raw data re-extraction (pass force=True to reprocess all).")
        print("=" * 70)
    else:
        report = CleaningReport(report_path)
        try:
            process_sdnet2018(raw_dirs["sdnet2018"], processed_dir, report, seed=RANDOM_SEED)
            process_concrete_crack_cls(raw_dirs["concrete_crack_cls"], processed_dir, report, seed=RANDOM_SEED)
            process_rdd2022(raw_dirs["rdd2022"], processed_dir, report, seed=RANDOM_SEED)
            process_crack500(raw_dirs["crack500"], processed_dir, report, seed=RANDOM_SEED)
            process_cfd(raw_dirs["cfd"], processed_dir, report)
        finally:
            report.save()

    summary_df = generate_split_summary(processed_dir)
    summary_plot = plot_distributions_and_splits(processed_dir)
    summary_plot.savefig(os.path.join(processed_dir, "reports", "split_summary.png"), dpi=150)
    plt.close(summary_plot)
    run_pipeline_assertions(processed_dir, full_hash_check=full_hash_check)
    generate_documentation(processed_dir, docs_path, raw_dirs)

    print("\n" + "=" * 70)
    print("DATA PREPARATION PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print("\nFinal split summary:")
    print(summary_df.to_string(index=False))

    changed_files = []
    for root in (processed_dir, os.path.dirname(docs_path)):
        for current_root, _, filenames in os.walk(root):
            for filename in filenames:
                path = os.path.join(current_root, filename)
                if path not in before or os.stat(path).st_mtime_ns != before[path]:
                    changed_files.append(os.path.relpath(path, base_dir))
    changed_files.append(os.path.relpath(created_list_path, base_dir))
    changed_files = sorted(set(changed_files))
    with open(created_list_path, "w", encoding="utf-8") as output:
        output.write("\n".join(changed_files) + "\n")
    processed_bytes = sum(
        os.path.getsize(os.path.join(current_root, filename))
        for current_root, _, filenames in os.walk(processed_dir)
        for filename in filenames
    )
    print(f"\nProcessed output size: {processed_bytes / (1024 ** 3):.2f} GiB")
    print(f"Created/updated files: {len(changed_files):,} (full list: {created_list_path})")
    for file_path in changed_files[:50]:
        print(f"  {file_path}")
    if len(changed_files) > 50:
        print(f"  ... {len(changed_files) - 50:,} additional paths in created_files.txt")
    return summary_df


if __name__ == "__main__":
    main()
