"""Colab Detection Packaging Script for InfraScan AI.

Creates the deployment ZIP archives for training and evaluating YOLO models
on Google Colab:
1. data/processed/colab_zips/rdd2022_yolo_small.zip (subsampled & resized RDD2022 dataset)
2. data/processed/colab_zips/ml_code_detection.zip (detection code and config)

Runs thorough integrity checks:
- zipfile.testzip() CRC validation
- 1:1 Image-to-Label parity check
- Strict relative path structure check
- Archive size reporting against Google Colab quotas (< 3 GB)
"""

import os
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Set, Tuple

BASE_DIR = Path(r"D:\Infosys springboards")
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
COLAB_ZIPS_DIR = DATA_PROCESSED_DIR / "colab_zips"
RDD_SMALL_DIR = DATA_PROCESSED_DIR / "rdd2022_yolo_small"
ML_DIR = BASE_DIR / "infrascan" / "ml"

MAX_ALLOWED_ZIP_BYTES = 3 * 1024 * 1024 * 1024  # 3 GB


def build_dataset_zip() -> Path:
    """Package data/processed/rdd2022_yolo_small into colab_zips/rdd2022_yolo_small.zip."""
    if not RDD_SMALL_DIR.exists():
        raise FileNotFoundError(
            f"Dataset directory not found: {RDD_SMALL_DIR}. Please run dataset generation first."
        )

    COLAB_ZIPS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = COLAB_ZIPS_DIR / "rdd2022_yolo_small.zip"
    print(f"\n[PACKAGE] Building dataset archive: {zip_path}...")

    # Collect files
    file_list: List[Tuple[Path, str]] = []
    for root, _, files in os.walk(RDD_SMALL_DIR):
        for f in files:
            full_path = Path(root) / f
            # Store with prefix rdd2022_yolo_small/<relative_path>
            rel_path = full_path.relative_to(RDD_SMALL_DIR)
            arcname = f"rdd2022_yolo_small/{rel_path.as_posix()}"
            file_list.append((full_path, arcname))

    print(f"Adding {len(file_list):,} files to {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for idx, (fpath, arcname) in enumerate(file_list):
            zf.write(fpath, arcname)
            if (idx + 1) % 2500 == 0 or (idx + 1) == len(file_list):
                print(f"  Archived {idx + 1:,} / {len(file_list):,} files...")

    size_bytes = zip_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    print(f"[OK] Created {zip_path.name}: {size_mb:.2f} MB ({size_bytes:,} bytes)")

    if size_bytes > MAX_ALLOWED_ZIP_BYTES:
        print(f"[WARNING] Archive size ({size_mb:.2f} MB) exceeds 3 GB limit!")
    else:
        print(f"[OK] Archive size is well within the 3 GB quota ({size_mb:.2f} MB < 3,072 MB).")

    return zip_path


def build_code_zip() -> Path:
    """Package detection source code into colab_zips/ml_code_detection.zip."""
    COLAB_ZIPS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = COLAB_ZIPS_DIR / "ml_code_detection.zip"
    print(f"\n[PACKAGE] Building detection code archive: {zip_path}...")

    # Files to include
    include_patterns = [
        ("__init__.py", "ml/__init__.py"),
        ("data_prep.py", "ml/data_prep.py"),
        ("detection/__init__.py", "ml/detection/__init__.py"),
        ("detection/config.py", "ml/detection/config.py"),
        ("detection/train_yolo.py", "ml/detection/train_yolo.py"),
        ("detection/evaluate_yolo.py", "ml/detection/evaluate_yolo.py"),
    ]

    # Exclusions
    excluded_keywords = [".env", "venv", "__pycache__", ".pt", ".pth", ".git"]

    files_to_pack: List[Tuple[Path, str]] = []
    for rel_src, arcname in include_patterns:
        src_path = ML_DIR / rel_src
        if src_path.exists():
            files_to_pack.append((src_path, arcname))
        else:
            print(f"[!] Warning: Code file not found: {src_path}")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fpath, arcname in files_to_pack:
            # Check exclusions
            if any(k in str(fpath).lower() for k in excluded_keywords):
                continue
            zf.write(fpath, arcname)
            print(f"  + Added: {arcname}")

    size_kb = zip_path.stat().st_size / 1024
    print(f"[OK] Created {zip_path.name}: {size_kb:.2f} KB")
    return zip_path


def verify_zip_integrity(zip_path: Path, is_dataset: bool = False) -> bool:
    """Run comprehensive integrity and parity checks on a zip archive."""
    print(f"\n[INTEGRITY] Verifying {zip_path.name}...")
    if not zip_path.exists():
        print(f"[ERROR] File does not exist: {zip_path}")
        return False

    with zipfile.ZipFile(zip_path, "r") as zf:
        # 1. CRC test
        corrupt = zf.testzip()
        if corrupt is not None:
            print(f"[ERROR] CRC check failed for file: {corrupt}")
            return False
        print("  [PASS] testzip() CRC verification successful (no corruption).")

        namelist = zf.namelist()

        # 2. Relative path check (no absolute paths or drive letters)
        for name in namelist:
            if name.startswith("/") or name.startswith("\\") or ":" in name or ".." in name:
                print(f"[ERROR] Non-relative or unsafe path detected: {name}")
                return False
        print(f"  [PASS] All {len(namelist):,} entries use safe, relative POSIX paths.")

        # 3. If dataset zip, check image/label parity across splits
        if is_dataset:
            for split in ["train", "val", "test"]:
                img_prefix = f"rdd2022_yolo_small/images/{split}/"
                lbl_prefix = f"rdd2022_yolo_small/labels/{split}/"

                img_stems = {
                    Path(n).stem
                    for n in namelist
                    if n.startswith(img_prefix) and n.endswith(".jpg")
                }
                lbl_stems = {
                    Path(n).stem
                    for n in namelist
                    if n.startswith(lbl_prefix) and n.endswith(".txt")
                }

                if img_stems != lbl_stems:
                    missing_labels = img_stems - lbl_stems
                    missing_images = lbl_stems - img_stems
                    print(f"[ERROR] Parity mismatch in {split}:")
                    if missing_labels:
                        print(f"  Missing labels for images: {list(missing_labels)[:5]}")
                    if missing_images:
                        print(f"  Missing images for labels: {list(missing_images)[:5]}")
                    return False

                print(f"  [PASS] Split '{split}' exact 1:1 image-to-label parity verified ({len(img_stems):,} pairs).")

            # Check data.yaml presence
            yaml_entry = "rdd2022_yolo_small/data.yaml"
            if yaml_entry not in namelist:
                print(f"[ERROR] Missing {yaml_entry} in archive!")
                return False
            print("  [PASS] data.yaml present in archive.")

    return True


def main():
    print("=" * 70)
    print("InfraScan AI - Detection Colab Package Builder")
    print("=" * 70)

    # 1. Package dataset
    dataset_zip = build_dataset_zip()
    ds_ok = verify_zip_integrity(dataset_zip, is_dataset=True)

    # 2. Package code
    code_zip = build_code_zip()
    code_ok = verify_zip_integrity(code_zip, is_dataset=False)

    print("\n" + "=" * 70)
    print("PACKAGING SUMMARY:")
    print(f"  Dataset Archive : {dataset_zip} ({dataset_zip.stat().st_size / (1024 * 1024):.2f} MB)")
    print(f"  Code Archive    : {code_zip} ({code_zip.stat().st_size / 1024:.2f} KB)")
    print(f"  Dataset Integrity Check : {'PASSED' if ds_ok else 'FAILED'}")
    print(f"  Code Integrity Check    : {'PASSED' if code_ok else 'FAILED'}")
    print("=" * 70)

    if not (ds_ok and code_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()

