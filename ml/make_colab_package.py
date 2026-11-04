"""
Packaging utility for Google Colab training.
Generates:
1. data/processed/manifests_colab/ (CSVs with relative forward-slash paths)
2. data/processed/colab_zips/classification_data.zip (images from manifests + colab manifests)
3. data/processed/colab_zips/ml_code.zip (infrascan/ml + app/ai/preprocessing.py & quality.py)
"""

import os
from pathlib import Path
import zipfile
import pandas as pd


def create_colab_manifests(
    processed_dir: Path,
    raw_dir: Path,
    output_manifests_dir: Path,
) -> tuple[Path, Path]:
    """Create manifests with paths relative to data/raw and forward slashes."""
    output_manifests_dir.mkdir(parents=True, exist_ok=True)

    manifest_names = ["concrete_crack_cls.csv", "sdnet2018.csv"]
    created_paths = []

    for name in manifest_names:
        src_csv = processed_dir / "manifests" / name
        dst_csv = output_manifests_dir / name

        if not src_csv.exists():
            raise FileNotFoundError(f"Source manifest missing: {src_csv}")

        df = pd.read_csv(src_csv)

        def to_rel_forward(p: str) -> str:
            norm = str(p).replace("\\", "/")
            if "data/raw/" in norm:
                rel = norm.split("data/raw/", 1)[1]
            else:
                rel = os.path.basename(p)
            return rel.lstrip("/")

        df["path"] = df["path"].apply(to_rel_forward)
        df.to_csv(dst_csv, index=False)
        created_paths.append(dst_csv)
        print(f"[Manifest] Created Colab manifest: {dst_csv} ({len(df):,} rows)")

    return created_paths[0], created_paths[1]


def build_classification_data_zip(
    manifest_paths: list[Path],
    raw_dir: Path,
    output_zip_path: Path,
) -> int:
    """Pack ONLY the images listed in the manifests plus the colab manifests into a zip file."""
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)
    if output_zip_path.exists():
        output_zip_path.unlink()

    added_files = set()

    print(f"\n[Zip: Data] Packaging classification data into: {output_zip_path}...")
    # Use ZIP_STORED since JPEG images are already compressed; this speeds up packaging significantly
    with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        # 1. Add colab manifests to zip under manifests_colab/
        for mp in manifest_paths:
            arcname = f"manifests_colab/{mp.name}"
            zf.write(mp, arcname=arcname)
            added_files.add(arcname)

        # 2. Add only the images referenced in the manifests
        for mp in manifest_paths:
            df = pd.read_csv(mp)
            print(f"  - Reading {len(df):,} image references from {mp.name}...")
            for rel_path in df["path"]:
                norm_rel = rel_path.replace("\\", "/").lstrip("/")
                if norm_rel in added_files:
                    continue

                abs_file_path = raw_dir / Path(norm_rel)
                if not abs_file_path.exists():
                    raise FileNotFoundError(f"Image referenced in {mp.name} missing: {abs_file_path}")

                zf.write(abs_file_path, arcname=norm_rel)
                added_files.add(norm_rel)

    size_mb = output_zip_path.stat().st_size / (1024 * 1024)
    print(f"[Zip: Data] Finished {output_zip_path.name}: {len(added_files):,} files, {size_mb:.1f} MB")
    return len(added_files)


def build_ml_code_zip(
    infrascan_dir: Path,
    output_zip_path: Path,
) -> int:
    """
    Pack infrascan/ml (excluding venv, __pycache__, models) plus backend/app/ai/preprocessing.py
    and quality.py (with an importable app/ structure) into ml_code.zip.
    """
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)
    added_count = 0
    ml_dir = infrascan_dir / "ml"
    backend_dir = infrascan_dir / "backend"

    print(f"\n[Zip: Code] Packaging ML code into: {output_zip_path}...")
    with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Pack ml/ directory
        for root, dirs, files in os.walk(ml_dir):
            # Prune excluded directories
            dirs[:] = [
                d for d in dirs
                if d not in ("venv", "__pycache__", "models", ".pytest_cache", ".git")
            ]
            for file in files:
                if file.endswith((".pyc", ".pyo")):
                    continue
                file_path = Path(root) / file
                rel_to_infrascan = file_path.relative_to(infrascan_dir).as_posix()
                zf.write(file_path, arcname=rel_to_infrascan)
                added_count += 1

        # 2. Pack shared AI preprocessing & quality modules under app/ai/
        prep_src = backend_dir / "app" / "ai" / "preprocessing.py"
        qual_src = backend_dir / "app" / "ai" / "quality.py"

        if not prep_src.exists():
            raise FileNotFoundError(f"Missing shared preprocessing module: {prep_src}")
        if not qual_src.exists():
            raise FileNotFoundError(f"Missing shared quality module: {qual_src}")

        # Add app package markers so 'from app.ai.preprocessing import ...' works directly in Colab
        zf.writestr("app/__init__.py", '"""InfraScan app package for Colab."""\n')
        zf.writestr("app/ai/__init__.py", '"""InfraScan app.ai package for Colab."""\n')

        # Add a lightweight standalone app/config.py to satisfy quality.py's settings import without pydantic
        standalone_config = '''"""Lightweight standalone configuration for Colab environment."""
class Settings:
    BLUR_THRESHOLD: float = 100.0
    BRIGHTNESS_MIN: float = 50.0
    BRIGHTNESS_MAX: float = 220.0
    MODEL_INPUT_SIZE: int = 256
    NORMALIZE_MODE: str = "zero_one"
    ENABLE_CONTRAST: bool = True
    ENABLE_DENOISE: bool = False
    ENABLE_SHARPEN: bool = False
    CLAHE_CLIP_LIMIT: float = 2.0
    CLAHE_TILE_GRID: int = 8

settings = Settings()
'''
        zf.writestr("app/config.py", standalone_config)

        zf.write(prep_src, arcname="app/ai/preprocessing.py")
        zf.write(qual_src, arcname="app/ai/quality.py")
        added_count += 5

    size_mb = output_zip_path.stat().st_size / (1024 * 1024)
    print(f"[Zip: Code] Finished {output_zip_path.name}: {added_count:,} files, {size_mb:.2f} MB")
    return added_count


def main():
    base_dir = Path(r"D:\Infosys springboards")
    infrascan_dir = base_dir / "infrascan"
    processed_dir = base_dir / "data" / "processed"
    raw_dir = base_dir / "data" / "raw"

    manifests_colab_dir = processed_dir / "manifests_colab"
    colab_zips_dir = processed_dir / "colab_zips"

    print("=" * 70)
    print("STARTING GOOGLE COLAB PACKAGE GENERATION")
    print("=" * 70)

    # 1. Create manifests_colab
    m_concrete, m_sdnet = create_colab_manifests(processed_dir, raw_dir, manifests_colab_dir)

    # 2. Package classification_data.zip
    data_zip = colab_zips_dir / "classification_data.zip"
    build_classification_data_zip([m_concrete, m_sdnet], raw_dir, data_zip)

    # 3. Package ml_code.zip
    code_zip = colab_zips_dir / "ml_code.zip"
    build_ml_code_zip(infrascan_dir, code_zip)

    print("\n" + "=" * 70)
    print("COLAB PACKAGE GENERATION SUMMARY:")
    print(f"1. Manifests Colab:    {manifests_colab_dir}")
    print(f"2. Classification Zip: {data_zip} ({data_zip.stat().st_size / (1024*1024):.1f} MB)")
    print(f"3. ML Code Zip:        {code_zip} ({code_zip.stat().st_size / (1024*1024):.2f} MB)")
    print("=" * 70)


if __name__ == "__main__":
    main()

