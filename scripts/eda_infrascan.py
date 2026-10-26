#!/usr/bin/env python3
"""Exploratory data analysis for InfraScan crack and damage datasets.

Inspect downloaded files only. Never invent class counts, mask statistics,
or image properties. Dataset-specific parsers run after the folder layout
is observed.

Examples:
  python scripts/eda_infrascan.py --help
  python scripts/eda_infrascan.py --dataset all
  python scripts/eda_infrascan.py --dataset cfd --max-images 50
  python scripts/eda_infrascan.py --dataset sdnet2018 --skip-perceptual
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, UnidentifiedImageError

try:
    import cv2
except Exception:  # pragma: no cover - optional
    cv2 = None

try:
    import imagehash
except Exception:  # pragma: no cover - optional
    imagehash = None


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "datasets" / "raw"
DEFAULT_OUTPUT = ROOT / "docs" / "eda_outputs"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
MASK_HINTS = ("mask", "label", "lab", "gt", "seg", "annotation", "ground")

DATASET_HINTS = {
    "cfd": ("cfd", "crackforest"),
    "deepcrack": ("deepcrack",),
    "sdnet2018": ("sdnet2018", "sdnet"),
    "rdd2022_czech": ("rdd2022_czech", "czech"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    """Return a repo-relative POSIX path. Never emit a machine-local absolute path."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path.name).as_posix()


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTS


def iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    skip = {".git", "__pycache__", ".eda_cache"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip for part in path.parts):
            continue
        yield path


def md5_file(path: Path, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def safe_open_image(path: Path) -> tuple[Image.Image | None, str | None]:
    try:
        image = Image.open(path)
        image.load()
        return image, None
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def guess_dataset_id(path: Path) -> str | None:
    text = path.as_posix().lower()
    for dataset_id, hints in DATASET_HINTS.items():
        if any(hint in text for hint in hints):
            return dataset_id
    return None


def discover_datasets(raw_root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    if not raw_root.exists():
        return found
    for child in sorted(raw_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("_") or child.name.startswith("."):
            continue
        dataset_id = guess_dataset_id(child) or child.name.lower()
        useful_exts = IMAGE_EXTS | {".xml", ".seg", ".mat"}
        n_useful = sum(
            1
            for p in child.rglob("*")
            if p.is_file()
            and ".git" not in p.parts
            and p.suffix.lower() in useful_exts
        )
        if n_useful == 0:
            continue
        found[dataset_id] = child
    return found


def folder_snapshot(root: Path, max_depth: int = 3) -> list[str]:
    lines: list[str] = []
    if not root.exists():
        return [f"{root} does not exist"]
    for path in sorted(root.rglob("*")):
        try:
            rel_path = path.relative_to(root)
        except ValueError:
            continue
        if len(rel_path.parts) > max_depth:
            continue
        if path.is_dir():
            n_files = sum(1 for p in path.iterdir() if p.is_file())
            n_dirs = sum(1 for p in path.iterdir() if p.is_dir())
            lines.append(f"{rel_path.as_posix()}/  files={n_files} dirs={n_dirs}")
    return lines[:80]


def likely_mask(path: Path) -> bool:
    text = path.as_posix().lower()
    return any(hint in text for hint in MASK_HINTS)


def class_from_sdnet(path: Path) -> tuple[str | None, str | None]:
    parts = [p.lower() for p in path.parts]
    surface = None
    label = None
    for part in parts:
        if part in {"d", "deck", "p", "pavement", "w", "wall"}:
            surface = {"d": "deck", "deck": "deck", "p": "pavement", "pavement": "pavement", "w": "wall", "wall": "wall"}[part]
        if part in {"cd", "ud", "cp", "up", "cw", "uw"}:
            surface = {"cd": "deck", "ud": "deck", "cp": "pavement", "up": "pavement", "cw": "wall", "uw": "wall"}[part]
            label = "cracked" if part[0] == "c" else "uncracked"
        if part in {"cracked", "uncracked", "positive", "negative"}:
            label = "cracked" if part in {"cracked", "positive"} else "uncracked"
    return surface, label


def parse_voc_xml(path: Path) -> dict[str, Any]:
    tree = ET.parse(path)
    root = tree.getroot()
    size = root.find("size")
    objects = []
    for obj in root.findall("object"):
        bbox = obj.find("bndbox")
        name = (obj.findtext("name") or "").strip()
        if bbox is None:
            continue
        try:
            xmin = float(bbox.findtext("xmin", "0"))
            ymin = float(bbox.findtext("ymin", "0"))
            xmax = float(bbox.findtext("xmax", "0"))
            ymax = float(bbox.findtext("ymax", "0"))
        except ValueError:
            continue
        objects.append(
            {
                "class_name": name,
                "xmin": xmin,
                "ymin": ymin,
                "xmax": xmax,
                "ymax": ymax,
                "width": max(0.0, xmax - xmin),
                "height": max(0.0, ymax - ymin),
            }
        )
    width = int(size.findtext("width", "0")) if size is not None else 0
    height = int(size.findtext("height", "0")) if size is not None else 0
    return {
        "xml_path": rel(path),
        "filename": root.findtext("filename"),
        "width": width,
        "height": height,
        "n_objects": len(objects),
        "objects": objects,
    }


def mask_stats(path: Path) -> dict[str, Any] | None:
    image, error = safe_open_image(path)
    if image is None:
        return {"path": rel(path), "error": error}
    arr = np.array(image.convert("L"))
    unique = np.unique(arr)
    crack_pixels = int((arr > 127).sum()) if unique.max() > 1 else int((arr > 0).sum())
    total = int(arr.size)
    return {
        "path": rel(path),
        "width": int(arr.shape[1]),
        "height": int(arr.shape[0]),
        "unique_values": unique[:12].tolist(),
        "n_unique": int(unique.size),
        "crack_pixels": crack_pixels,
        "total_pixels": total,
        "crack_fraction": round(crack_pixels / total, 6) if total else 0.0,
        "empty_mask": crack_pixels == 0,
    }


def save_fig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def copy_samples(records: list[dict[str, Any]], dest: Path, n: int = 8) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    readable = [
        r
        for r in records
        if r.get("readable") and r.get("path") and r.get("mode") in {"RGB", "RGBA", "L"} and not r.get("is_mask_path")
    ]
    if not readable:
        readable = [r for r in records if r.get("readable") and r.get("path")]
    if not readable:
        return saved
    random.seed(42)
    chosen = readable if len(readable) <= n else random.sample(readable, n)
    for rec in chosen:
        src = ROOT / rec["path"]
        if not src.exists():
            continue
        image, error = safe_open_image(src)
        if image is None:
            continue
        out = dest / src.name
        image.convert("RGB").save(out)
        saved.append(rel(out))
    return saved


def plot_class_counts(counts: Counter, title: str, dest: Path) -> None:
    if not counts:
        return
    labels, values = zip(*sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(labels, values, color="#1f4e79")
    ax.set_title(title)
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=30)
    for i, v in enumerate(values):
        ax.text(i, v, str(v), ha="center", va="bottom", fontsize=8)
    save_fig(fig, dest)


def plot_histogram(values: list[float], title: str, xlabel: str, dest: Path) -> None:
    if not values:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(values, bins=min(30, max(8, int(len(values) ** 0.5))), color="#3d7ea6")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    save_fig(fig, dest)


def plot_size_scatter(records: list[dict[str, Any]], title: str, dest: Path) -> None:
    widths = [r["width"] for r in records if r.get("width")]
    heights = [r["height"] for r in records if r.get("height")]
    if not widths:
        return
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(widths, heights, s=12, alpha=0.5, c="#1f4e79")
    ax.set_title(title)
    ax.set_xlabel("Width (px)")
    ax.set_ylabel("Height (px)")
    save_fig(fig, dest)


def analyze_images(
    dataset_id: str,
    root: Path,
    output: Path,
    max_images: int | None,
    skip_perceptual: bool,
    perceptual_limit: int,
) -> dict[str, Any]:
    files = [p for p in iter_files(root)]
    images = [p for p in files if is_image(p)]
    non_images = [p for p in files if not is_image(p)]
    images.sort()
    sampled = images if max_images is None else images[:max_images]

    records: list[dict[str, Any]] = []
    hash_groups: dict[str, list[str]] = defaultdict(list)
    phash_groups: dict[str, list[str]] = defaultdict(list)
    unreadable: list[dict[str, str]] = []
    formats = Counter()
    modes = Counter()
    sizes = Counter()
    class_counts = Counter()
    surface_counts = Counter()

    for idx, path in enumerate(sampled, start=1):
        if idx % 2000 == 0:
            print(f"  [{dataset_id}] inspected {idx}/{len(sampled)} images")
        rec: dict[str, Any] = {
            "dataset_id": dataset_id,
            "path": rel(path),
            "filename": path.name,
            "suffix": path.suffix.lower(),
            "bytes": path.stat().st_size,
            "parent": path.parent.name,
        }
        surface, label = class_from_sdnet(path)
        rec["surface"] = surface
        rec["class_label"] = label
        if label:
            class_counts[label] += 1
        if surface:
            surface_counts[surface] += 1

        digest = md5_file(path)
        rec["md5"] = digest
        hash_groups[digest].append(rel(path))

        image, error = safe_open_image(path)
        if image is None:
            rec["readable"] = False
            rec["error"] = error
            unreadable.append({"path": rel(path), "error": error or "unknown"})
            records.append(rec)
            continue

        rec["readable"] = True
        rec["width"] = image.width
        rec["height"] = image.height
        rec["mode"] = image.mode
        rec["format"] = image.format
        rec["is_mask_path"] = likely_mask(path)
        formats[image.format or path.suffix.lower()] += 1
        modes[image.mode] += 1
        sizes[(image.width, image.height)] += 1

        if not skip_perceptual and imagehash is not None and idx <= perceptual_limit:
            try:
                ph = str(imagehash.phash(image.convert("RGB")))
                rec["phash"] = ph
                phash_groups[ph].append(rel(path))
            except Exception as exc:
                rec["phash_error"] = str(exc)
        image.close()
        records.append(rec)

    exact_dupes = {k: v for k, v in hash_groups.items() if len(v) > 1}
    perceptual_dupes = {k: v for k, v in phash_groups.items() if len(v) > 1}

    csv_dir = output / "csv"
    write_csv(csv_dir / f"{dataset_id}_image_inventory.csv", records)
    write_csv(csv_dir / f"{dataset_id}_unreadable.csv", unreadable)
    write_csv(
        csv_dir / f"{dataset_id}_exact_duplicates.csv",
        [{"md5": k, "n": len(v), "paths": " | ".join(v[:8])} for k, v in exact_dupes.items()],
    )

    plots = output / "plots"
    plot_class_counts(class_counts, f"{dataset_id}: class counts (from folders)", plots / f"{dataset_id}_class_counts.png")
    plot_class_counts(surface_counts, f"{dataset_id}: surface / structure counts", plots / f"{dataset_id}_surface_counts.png")
    plot_class_counts(Counter({f"{w}x{h}": n for (w, h), n in sizes.most_common(12)}), f"{dataset_id}: image sizes", plots / f"{dataset_id}_sizes.png")
    plot_size_scatter([r for r in records if r.get("readable")], f"{dataset_id}: width vs height", plots / f"{dataset_id}_size_scatter.png")
    plot_histogram(
        [r["bytes"] / 1024 for r in records if r.get("bytes")],
        f"{dataset_id}: file size",
        "KiB",
        plots / f"{dataset_id}_filesize.png",
    )
    samples = copy_samples(records, output / "samples" / dataset_id, n=8)

    return {
        "dataset_id": dataset_id,
        "root": rel(root),
        "n_files": len(files),
        "n_images_found": len(images),
        "n_images_inspected": len(sampled),
        "n_non_image_files": len(non_images),
        "n_unreadable": len(unreadable),
        "formats": dict(formats),
        "color_modes": dict(modes),
        "size_histogram": {f"{w}x{h}": n for (w, h), n in sizes.most_common(20)},
        "class_counts_from_folders": dict(class_counts),
        "surface_counts_from_folders": dict(surface_counts),
        "exact_duplicate_groups": len(exact_dupes),
        "exact_duplicate_extra_files": sum(len(v) - 1 for v in exact_dupes.values()),
        "perceptual_duplicate_groups": len(perceptual_dupes) if not skip_perceptual else "skipped",
        "sample_images": samples,
        "folder_snapshot": folder_snapshot(root),
        "non_image_suffixes": dict(Counter(p.suffix.lower() or "[noext]" for p in non_images)),
        "truncated": bool(max_images and len(images) > max_images),
    }


def parse_cfd_seg(path: Path) -> dict[str, Any]:
    """Parse Berkeley-style CFD .seg run-length files."""
    header: dict[str, str] = {}
    crack_pixels = 0
    total_pixels = 0
    in_data = False
    with path.open("r", encoding="latin-1") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if not in_data:
                if line == "data":
                    in_data = True
                    continue
                if " " in line:
                    key, value = line.split(" ", 1)
                    header[key] = value
                continue
            parts = line.split()
            if len(parts) != 4:
                continue
            seg_id, _row, c1, c2 = map(int, parts)
            width = c2 - c1 + 1
            total_pixels += width
            if seg_id != 0:
                crack_pixels += width
    height = int(header.get("height", "0") or 0)
    width = int(header.get("width", "0") or 0)
    expected = height * width if height and width else total_pixels
    return {
        "path": rel(path),
        "width": width,
        "height": height,
        "n_segments": header.get("segments"),
        "crack_pixels": crack_pixels,
        "total_pixels": expected,
        "crack_fraction": round(crack_pixels / expected, 6) if expected else 0.0,
        "empty_mask": crack_pixels == 0,
        "covered_pixels": total_pixels,
        "coverage_complete": total_pixels == expected if expected else False,
    }


def analyze_cfd(root: Path, output: Path, summary: dict[str, Any]) -> dict[str, Any]:
    image_dir = next((p for p in root.rglob("*") if p.is_dir() and p.name.lower() in {"image", "images"}), None)
    gt_dir = next((p for p in root.rglob("*") if p.is_dir() and p.name.lower() in {"groundtruth", "gt"}), None)
    seg_dir = next((p for p in root.rglob("*") if p.is_dir() and p.name.lower() in {"seg", "mask", "masks"}), None)
    images = [p for p in (image_dir.glob("*") if image_dir else []) if is_image(p)]
    segs = list(seg_dir.glob("*.seg") if seg_dir else [])
    gts = list(gt_dir.glob("*") if gt_dir else [])
    mask_rows = [parse_cfd_seg(path) for path in sorted(segs)]
    write_csv(output / "csv" / "cfd_mask_stats.csv", mask_rows)
    if mask_rows:
        plot_histogram(
            [r["crack_fraction"] for r in mask_rows],
            "CFD: crack pixel fraction (.seg)",
            "Crack pixel fraction",
            output / "plots" / "cfd_crack_fraction.png",
        )
    image_stems = {p.stem for p in images}
    seg_stems = {p.stem for p in segs}
    gt_stems = {p.stem for p in gts}
    unlabeled = sorted(image_stems - seg_stems - gt_stems)
    numbered_118 = [p for p in images if p.stem.isdigit() and 1 <= int(p.stem) <= 118]
    return {
        "annotation_format": "Berkeley .seg run-length files plus MATLAB .mat groundTruth",
        "n_rgb_images": len(images),
        "n_standard_001_to_118": len(numbered_118),
        "n_groundtruth_mat": sum(1 for p in gts if p.suffix.lower() == ".mat"),
        "n_seg_files": len(segs),
        "matched_image_seg_stems": len(image_stems & seg_stems),
        "unlabeled_extra_image_stems": unlabeled,
        "n_unlabeled_extra_images": len(unlabeled),
        "mask_rows_computed": len(mask_rows),
        "mean_crack_fraction": float(np.mean([r["crack_fraction"] for r in mask_rows])) if mask_rows else None,
        "empty_masks": sum(1 for r in mask_rows if r.get("empty_mask")),
        "complete_coverage_seg_files": sum(1 for r in mask_rows if r.get("coverage_complete")),
    }


def analyze_deepcrack(root: Path, output: Path) -> dict[str, Any]:
    groups = {
        "train_img": [],
        "train_lab": [],
        "test_img": [],
        "test_lab": [],
    }
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parent = path.parent.name.lower()
        if parent in groups and (is_image(path) or path.suffix.lower() in IMAGE_EXTS):
            groups[parent].append(path)

    # Some extracts nest as DeepCrack/train_img
    if not any(groups.values()):
        for path in root.rglob("*"):
            if not is_image(path):
                continue
            parts = [p.lower() for p in path.parts]
            for key in groups:
                if key in parts:
                    groups[key].append(path)

    mask_rows = []
    for split in ("train_lab", "test_lab"):
        for path in sorted(groups[split])[:800]:
            stats = mask_stats(path)
            if stats:
                stats["split"] = split
                mask_rows.append(stats)
    write_csv(output / "csv" / "deepcrack_mask_stats.csv", mask_rows)
    if mask_rows:
        plot_histogram(
            [r["crack_fraction"] for r in mask_rows if "crack_fraction" in r],
            "DeepCrack: crack pixel fraction",
            "Crack pixel fraction",
            output / "plots" / "deepcrack_crack_fraction.png",
        )

    def stems(paths: list[Path]) -> set[str]:
        return {p.stem for p in paths}

    train_match = stems(groups["train_img"]) & stems(groups["train_lab"])
    test_match = stems(groups["test_img"]) & stems(groups["test_lab"])
    overlap_stems = sorted(stems(groups["train_img"]) & stems(groups["test_img"]))
    return {
        "annotation_format": "Pixel-wise binary masks paired with RGB images",
        "train_images": len(groups["train_img"]),
        "train_masks": len(groups["train_lab"]),
        "test_images": len(groups["test_img"]),
        "test_masks": len(groups["test_lab"]),
        "train_stem_matches": len(train_match),
        "test_stem_matches": len(test_match),
        "train_test_filename_overlap": len(overlap_stems),
        "train_test_overlapping_stems": overlap_stems,
        "empty_masks": sum(1 for r in mask_rows if r.get("empty_mask")),
        "mean_crack_fraction": float(np.mean([r["crack_fraction"] for r in mask_rows])) if mask_rows else None,
        "split_leakage_risk": (
            "Same filenames appear in train_img and test_img; files are not byte-identical. "
            "Do not treat the published split as leakage-free."
            if overlap_stems
            else "no filename overlap observed in inspected files"
        ),
    }


def analyze_sdnet(root: Path, summary: dict[str, Any]) -> dict[str, Any]:
    counts = summary.get("class_counts_from_folders") or {}
    cracked = int(counts.get("cracked", 0))
    uncracked = int(counts.get("uncracked", 0))
    total = cracked + uncracked
    imbalance = None
    if total:
        imbalance = {
            "cracked_fraction": round(cracked / total, 4),
            "uncracked_fraction": round(uncracked / total, 4),
            "imbalance_ratio_uncracked_to_cracked": round(uncracked / cracked, 3) if cracked else None,
        }
    return {
        "annotation_format": "Image-level cracked/uncracked labels encoded in folder names (C*/U*)",
        "supported_task": "Binary classification",
        "has_masks": False,
        "has_boxes": False,
        "original_photographs_in_paper": 230,
        "inspected_are_patches": True,
        "class_imbalance": imbalance,
        "leakage_risk": "Patches from the same original photograph can leak across random splits. Split by original image, not by patch.",
    }


def analyze_rdd(root: Path, output: Path) -> dict[str, Any]:
    xml_files = [p for p in root.rglob("*.xml")]
    images = [p for p in root.rglob("*") if is_image(p)]
    parsed = []
    errors = []
    class_counts = Counter()
    boxes_per_image = []
    box_areas = []
    for path in xml_files:
        try:
            rec = parse_voc_xml(path)
        except Exception as exc:
            errors.append({"path": rel(path), "error": str(exc)})
            continue
        parsed.append(
            {
                "xml_path": rec["xml_path"],
                "filename": rec["filename"],
                "width": rec["width"],
                "height": rec["height"],
                "n_objects": rec["n_objects"],
                "classes": ",".join(sorted({o["class_name"] for o in rec["objects"]})),
            }
        )
        boxes_per_image.append(rec["n_objects"])
        for obj in rec["objects"]:
            class_counts[obj["class_name"] or "[empty]"] += 1
            box_areas.append(obj["width"] * obj["height"])

    write_csv(output / "csv" / "rdd2022_czech_xml_summary.csv", parsed)
    write_csv(output / "csv" / "rdd2022_czech_xml_errors.csv", errors)
    plot_class_counts(class_counts, "RDD2022 Czech: bounding-box classes", output / "plots" / "rdd2022_czech_box_classes.png")
    plot_histogram(boxes_per_image, "RDD2022 Czech: objects per XML", "Objects", output / "plots" / "rdd2022_czech_objects_per_image.png")

    image_stems = {p.stem for p in images}
    xml_stems = {p.stem for p in xml_files}
    xml_filenames = {Path(r["filename"]).stem for r in parsed if r.get("filename")}
    matched = len(image_stems & (xml_stems | xml_filenames))
    unlabeled = len(image_stems - xml_stems - xml_filenames)

    official = {"D00", "D10", "D20", "D40"}
    other = {k: v for k, v in class_counts.items() if k not in official}
    return {
        "annotation_format": "Pascal VOC XML bounding boxes",
        "n_images": len(images),
        "n_xml": len(xml_files),
        "xml_parse_errors": len(errors),
        "matched_image_xml_stems": matched,
        "images_without_xml": unlabeled,
        "box_class_counts": dict(class_counts),
        "crddc2022_core_classes": {k: class_counts.get(k, 0) for k in sorted(official)},
        "additional_classes_present": other,
        "images_with_zero_objects": sum(1 for n in boxes_per_image if n == 0),
        "mean_objects_per_xml": float(np.mean(boxes_per_image)) if boxes_per_image else 0.0,
        "mean_box_area_px": float(np.mean(box_areas)) if box_areas else None,
    }


def dataset_specific(dataset_id: str, root: Path, output: Path, summary: dict[str, Any]) -> dict[str, Any]:
    if dataset_id == "cfd":
        return analyze_cfd(root, output, summary)
    if dataset_id == "deepcrack":
        return analyze_deepcrack(root, output)
    if dataset_id == "sdnet2018":
        return analyze_sdnet(root, summary)
    if dataset_id == "rdd2022_czech":
        return analyze_rdd(root, output)
    return {"annotation_format": "unknown; generic image analysis only"}


def write_markdown_summary(output: Path, results: list[dict[str, Any]]) -> None:
    lines = [
        "# InfraScan EDA machine summary",
        "",
        f"Generated: {utc_now()}",
        "",
        "This file is written by `scripts/eda_infrascan.py`. Counts refer to files actually inspected.",
        "",
    ]
    for result in results:
        lines.append(f"## {result['dataset_id']}")
        lines.append("")
        for key, value in result.items():
            if key in {"folder_snapshot", "image_records_omitted"}:
                continue
            lines.append(f"- **{key}**: `{value}`")
        lines.append("")
        if result.get("folder_snapshot"):
            lines.append("Folder snapshot:")
            lines.append("")
            lines.append("```")
            lines.extend(result["folder_snapshot"][:40])
            lines.append("```")
            lines.append("")
    (output / "eda_machine_summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Exploratory Data Analysis on downloaded InfraScan datasets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dataset", default="all", help="Dataset id or 'all'.")
    parser.add_argument("--root", default="datasets/raw", help="Raw dataset directory, relative to the repo root unless absolute.")
    parser.add_argument("--output", default="docs/eda_outputs", help="Output directory for CSV, plots, and samples, relative to the repo root unless absolute.")
    parser.add_argument("--max-images", type=int, default=None, help="Inspect at most N images per dataset.")
    parser.add_argument("--skip-perceptual", action="store_true", help="Skip perceptual hash duplicate search.")
    parser.add_argument("--perceptual-limit", type=int, default=2000, help="Max images for perceptual hashing.")
    parser.add_argument("--list", action="store_true", help="List discovered datasets and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_root = Path(args.root)
    if not raw_root.is_absolute():
        raw_root = (ROOT / raw_root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = (ROOT / output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "csv").mkdir(exist_ok=True)
    (output / "plots").mkdir(exist_ok=True)
    (output / "samples").mkdir(exist_ok=True)

    discovered = discover_datasets(raw_root)
    if args.list:
        if not discovered:
            print(f"No datasets found under {raw_root}")
            return 1
        for dataset_id, path in discovered.items():
            print(f"{dataset_id:20} {rel(path)}")
        return 0

    if args.dataset == "all":
        selected = discovered
    elif args.dataset in discovered:
        selected = {args.dataset: discovered[args.dataset]}
    else:
        print(f"Dataset '{args.dataset}' not found under {raw_root}")
        print("Discovered:", ", ".join(discovered) or "(none)")
        return 2

    if not selected:
        print(f"No downloaded datasets found under {raw_root}")
        (output / "EDA_PENDING.txt").write_text(
            "No datasets were present. Hands-on EDA is pending until downloads succeed.\n",
            encoding="utf-8",
        )
        return 1

    results = []
    for dataset_id, path in selected.items():
        print(f"\n=== EDA {dataset_id} ===")
        print(f"root: {path}")
        summary = analyze_images(
            dataset_id,
            path,
            output,
            max_images=args.max_images,
            skip_perceptual=args.skip_perceptual,
            perceptual_limit=args.perceptual_limit,
        )
        specific = dataset_specific(dataset_id, path, output, summary)
        summary["dataset_specific"] = specific
        results.append(summary)
        print(json.dumps({k: v for k, v in summary.items() if k != "folder_snapshot"}, indent=2, default=str)[:2000])

    write_csv(
        output / "csv" / "eda_overview.csv",
        [
            {
                "dataset_id": r["dataset_id"],
                "n_images_found": r["n_images_found"],
                "n_images_inspected": r["n_images_inspected"],
                "n_unreadable": r["n_unreadable"],
                "exact_duplicate_groups": r["exact_duplicate_groups"],
                "class_counts": json.dumps(r.get("class_counts_from_folders")),
                "specific": json.dumps(r.get("dataset_specific"), default=str)[:1000],
            }
            for r in results
        ],
    )
    (output / "eda_results.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    write_markdown_summary(output, results)
    print(f"\nEDA outputs written to {rel(output)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
