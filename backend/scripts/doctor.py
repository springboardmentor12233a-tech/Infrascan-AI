#!/usr/bin/env python3
"""
InfraScan System Health & Diagnostic Tool (doctor.py)
Checks:
1. Python and Node.js runtimes
2. Database connectivity and migration integrity
3. Required Python dependencies & PyTorch CPU build
4. Model weights resolution, file sizes, and SHA-256 hashes
5. CPU smoke inference verification on generated dummy image
6. Storage directories & disk space
7. Server port availability (8000, 5173)
Safe '--fix' mode creates missing directories and runs pending migrations.
"""

import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

# Add backend root to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

project_root = backend_dir.parent


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f" {title.upper()}")
    print("=" * 70)


def check_runtime():
    print_header("1. Runtime Environment")
    py_ver = sys.version.split()[0]
    print(f"[OK] Python runtime: {py_ver} ({sys.executable})")

    # Check Node.js
    try:
        node_out = subprocess.check_output(["node", "--version"], text=True, stderr=subprocess.DEVNULL).strip()
        print(f"[OK] Node.js: {node_out}")
    except Exception:
        print("[WARN] Node.js is not found in PATH. Frontend build requires Node v18+.")


def check_database():
    print_header("2. Database Connectivity & Migrations")
    try:
        from app.database import engine
        from sqlalchemy import text, inspect

        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            print(f"[OK] Database connection successful: {engine.dialect.name}")

            inspector = inspect(conn)
            tables = inspector.get_table_names()
            print(f"[OK] Tables found ({len(tables)}): {', '.join(sorted(tables)[:10])}...")

            expected_tables = ["users", "infrastructure_assets", "inspections", "images", "analysis_runs", "events"]
            missing = [t for t in expected_tables if t not in tables]
            if missing:
                print(f"[FAIL] Missing critical tables: {missing}")
                return False
            else:
                print("[OK] All critical schema tables present.")
        return True
    except Exception as e:
        print(f"[FAIL] Database check failed: {e}")
        return False


def check_packages():
    print_header("3. Python Package Dependencies")
    required = [
        "torch",
        "ultralytics",
        "segmentation_models_pytorch",
        "cv2",
        "skimage",
        "scipy",
        "PIL",
        "reportlab",
        "openpyxl",
        "fastapi",
        "pydantic",
        "sqlalchemy",
    ]
    all_ok = True
    for pkg in required:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "installed")
            if pkg == "torch":
                cuda_avail = mod.cuda.is_available()
                print(f"[OK] torch: {ver} (CUDA available: {cuda_avail}, CPU mode active)")
            else:
                print(f"[OK] {pkg}: {ver}")
        except ImportError:
            print(f"[FAIL] Missing package: {pkg}")
            all_ok = False
    return all_ok


def check_model_weights():
    print_header("4. Model Weights & Hashes")
    from app.config import settings

    weights_to_check = [
        ("YOLO Road Defect Detector", settings.YOLO_WEIGHTS),
        ("U-Net++ Crack Segmentation", settings.SEG_WEIGHTS),
        ("CodeBRIM Defect Detector", settings.CODEBRIM_WEIGHTS),
    ]

    from app.services.analysis_service import resolve_disk_path

    for name, path_str in weights_to_check:
        resolved = resolve_disk_path(path_str)
        if resolved.exists():
            size_mb = resolved.stat().st_size / (1024 * 1024)
            # Compute sha256 of first 4MB for fast smoke check
            h = hashlib.sha256()
            with open(resolved, "rb") as f:
                h.update(f.read(4 * 1024 * 1024))
            short_sha = h.hexdigest()[:16]
            print(f"[OK] {name}: {resolved} ({size_mb:.2f} MB, sha256_prefix={short_sha})")
        else:
            print(f"[WARN] {name} weights file not found: {resolved}")


def check_smoke_inference():
    print_header("5. Smoke CPU Inference Test")
    try:
        import numpy as np
        import torch
        from app.config import settings
        from app.services.analysis_service import get_segmentation_model, resolve_disk_path

        seg_path = resolve_disk_path(settings.SEG_WEIGHTS)
        if seg_path.exists():
            print("[INFO] Loading U-Net++ ResNet-34 on CPU for smoke inference...")
            model = get_segmentation_model(settings.SEG_WEIGHTS)
            dummy_input = torch.zeros((1, 3, 256, 256), dtype=torch.float32)
            with torch.inference_mode():
                out = model(dummy_input)
            print(f"[OK] Segmentation model CPU smoke inference succeeded. Output shape: {out.shape}")
        else:
            print("[SKIP] Segmentation model weights missing; skipping smoke inference.")
    except Exception as e:
        print(f"[FAIL] Smoke inference test failed: {e}")


def check_ports():
    print_header("6. Port Availability")
    ports = [(8000, "Backend API"), (5173, "Frontend Vite Dev Server")]
    for port, label in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            is_busy = s.connect_ex(("127.0.0.1", port)) == 0
            if is_busy:
                print(f"[INFO] Port {port} ({label}) is currently ACTIVE/OCCUPIED.")
            else:
                print(f"[OK] Port {port} ({label}) is FREE.")


def check_disk_space():
    print_header("7. Disk Space")
    for drive in ["C:\\", "D:\\"]:
        if os.path.exists(drive):
            total, used, free = shutil.disk_usage(drive)
            free_gb = free / (1024**3)
            print(f"[OK] Drive {drive}: {free_gb:.2f} GB free")


def run_doctor(fix: bool = False):
    print("=" * 70)
    print(" INFRASCAN SYSTEM DOCTOR & PRE-FLIGHT DIAGNOSTIC")
    print("=" * 70)

    check_runtime()
    db_ok = check_database()
    pkg_ok = check_packages()
    check_model_weights()
    check_smoke_inference()
    check_ports()
    check_disk_space()

    if fix:
        print_header("Executing Safe Fix Operations (--fix)")
        from app.config import settings
        for p in [settings.images_path, settings.processed_path, settings.mask_path, settings.reports_path]:
            p.mkdir(parents=True, exist_ok=True)
            print(f"[FIX] Created directory: {p}")

        from scripts.init_db import init_database
        init_database()
        print("[FIX] Migrations verified and applied.")

    print("\n" + "=" * 70)
    print(" DOCTOR DIAGNOSIS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="InfraScan Doctor Diagnostic Tool")
    parser.add_argument("--fix", action="store_true", help="Perform safe automated fixes")
    args = parser.parse_args()
    run_doctor(fix=args.fix)
