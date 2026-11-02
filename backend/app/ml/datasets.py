"""Dataset helpers for the local CFD, DeepCrack, and RDD2022 Czech files.

These functions read the files already on disk. They do not download data
and they do not modify the original images or annotations.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterator

import cv2
import numpy as np

from app.ml.paths import (
    CFD_ROOT,
    DEEPCRACK_ROOT,
    RDD_TRAIN_IMAGES,
    RDD_TRAIN_XML,
)

# RDD2022 / CRDDC class ids used by the Czech subset.
RDD_CLASS_TO_ID = {
    "D00": 0,  # longitudinal crack
    "D10": 1,  # transverse crack
    "D20": 2,  # alligator crack
    "D40": 3,  # pothole
}
RDD_ID_TO_CLASS = {index: name for name, index in RDD_CLASS_TO_ID.items()}
RDD_CLASS_DESCRIPTIONS = {
    "D00": "Longitudinal crack",
    "D10": "Transverse crack",
    "D20": "Alligator crack",
    "D40": "Pothole",
}


def source_group(stem: str) -> str:
    """Group DeepCrack crops that come from the same source photo.

    `11289-1` and `11289-10` share the group `11289`. A stem with no numeric
    suffix is its own group. This is the split key recommended by the EDA.
    """
    if "-" in stem:
        head, tail = stem.rsplit("-", 1)
        if tail.isdigit() and head:
            return head
    return stem


def list_deepcrack_pairs() -> list[dict[str, Any]]:
    """Return matched DeepCrack image/mask pairs from train and test folders."""
    pairs: list[dict[str, Any]] = []
    splits = (
        ("train", DEEPCRACK_ROOT / "train_img", DEEPCRACK_ROOT / "train_lab"),
        ("test", DEEPCRACK_ROOT / "test_img", DEEPCRACK_ROOT / "test_lab"),
    )
    for split, image_dir, mask_dir in splits:
        if not image_dir.is_dir() or not mask_dir.is_dir():
            continue
        masks = {path.stem: path for path in mask_dir.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg"}}
        for image_path in sorted(image_dir.iterdir()):
            if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            mask_path = masks.get(image_path.stem)
            if mask_path is None:
                continue
            pairs.append(
                {
                    "split_published": split,
                    "stem": image_path.stem,
                    "group": source_group(image_path.stem),
                    "image_path": image_path,
                    "mask_path": mask_path,
                }
            )
    return pairs


def load_binary_mask(path: Path, threshold: int = 127) -> np.ndarray:
    mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise ValueError(f"Could not read mask: {path}")
    return np.where(mask > threshold, 255, 0).astype(np.uint8)


def parse_voc_xml(path: Path) -> dict[str, Any]:
    """Parse one Pascal VOC file from RDD2022. Unknown classes are kept and flagged."""
    tree = ET.parse(path)
    root = tree.getroot()
    size = root.find("size")
    width = int(float(size.findtext("width", "0"))) if size is not None else 0
    height = int(float(size.findtext("height", "0"))) if size is not None else 0
    objects: list[dict[str, Any]] = []
    unknown: list[str] = []
    for obj in root.findall("object"):
        name = (obj.findtext("name") or "").strip()
        bbox = obj.find("bndbox")
        if bbox is None:
            continue
        try:
            xmin = float(bbox.findtext("xmin", "0"))
            ymin = float(bbox.findtext("ymin", "0"))
            xmax = float(bbox.findtext("xmax", "0"))
            ymax = float(bbox.findtext("ymax", "0"))
        except ValueError:
            continue
        class_id = RDD_CLASS_TO_ID.get(name)
        if class_id is None:
            unknown.append(name)
        objects.append(
            {
                "class_name": name,
                "class_id": class_id,
                "xmin": xmin,
                "ymin": ymin,
                "xmax": xmax,
                "ymax": ymax,
            }
        )
    return {
        "path": str(path),
        "filename": root.findtext("filename") or path.with_suffix(".jpg").name,
        "width": width,
        "height": height,
        "objects": objects,
        "unknown_classes": unknown,
    }


def voc_box_to_yolo(box: dict[str, Any], width: int, height: int) -> tuple[float, float, float, float] | None:
    """Convert one VOC box to normalized YOLO xywh. Returns None if the box is empty."""
    if width <= 0 or height <= 0 or box.get("class_id") is None:
        return None
    xmin = min(max(box["xmin"], 0.0), width)
    xmax = min(max(box["xmax"], 0.0), width)
    ymin = min(max(box["ymin"], 0.0), height)
    ymax = min(max(box["ymax"], 0.0), height)
    box_w = xmax - xmin
    box_h = ymax - ymin
    if box_w <= 1 or box_h <= 1:
        return None
    x_center = ((xmin + xmax) / 2.0) / width
    y_center = ((ymin + ymax) / 2.0) / height
    return (
        min(max(x_center, 0.0), 1.0),
        min(max(y_center, 0.0), 1.0),
        min(max(box_w / width, 0.0), 1.0),
        min(max(box_h / height, 0.0), 1.0),
    )


def iter_rdd_xml() -> Iterator[Path]:
    if not RDD_TRAIN_XML.is_dir():
        return
    yield from sorted(RDD_TRAIN_XML.glob("*.xml"))


def rdd_image_for_stem(stem: str) -> Path | None:
    candidate = RDD_TRAIN_IMAGES / f"{stem}.jpg"
    if candidate.is_file():
        return candidate
    return None


def parse_cfd_seg(path: Path) -> dict[str, Any]:
    """Parse a Berkeley-style CFD `.seg` run-length file. Does not build a mask."""
    header: dict[str, str] = {}
    crack_pixels = 0
    covered = 0
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
            span = c2 - c1 + 1
            covered += span
            if seg_id != 0:
                crack_pixels += span
    height = int(header.get("height", "0") or 0)
    width = int(header.get("width", "0") or 0)
    expected = height * width if height and width else covered
    return {
        "path": str(path),
        "width": width,
        "height": height,
        "crack_pixels": crack_pixels,
        "total_pixels": expected,
        "crack_fraction": round(crack_pixels / expected, 6) if expected else 0.0,
        "coverage_complete": covered == expected if expected else False,
    }


def cfd_seg_dir() -> Path | None:
    direct = CFD_ROOT / "seg"
    if direct.is_dir():
        return direct
    for path in CFD_ROOT.rglob("seg"):
        if path.is_dir():
            return path
    return None


def validate_image_file(path: Path) -> dict[str, Any]:
    """Open one image and report whether it can be decoded, plus its size."""
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        return {"path": str(path), "readable": False}
    height, width = image.shape[:2]
    channels = 1 if image.ndim == 2 else int(image.shape[2])
    return {
        "path": str(path),
        "readable": True,
        "width": int(width),
        "height": int(height),
        "channels": channels,
    }
