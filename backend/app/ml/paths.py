"""Shared filesystem locations. Paths do not depend on the process working directory."""

from pathlib import Path

# backend/app/ml/paths.py -> repo root is three parents up
REPO_ROOT = Path(__file__).resolve().parents[3]
WEIGHTS_DIR = REPO_ROOT / "models" / "weights"
REPORTS_DIR = REPO_ROOT / "models" / "reports"
DATASETS_RAW = REPO_ROOT / "datasets" / "raw"
DATASETS_PROCESSED = REPO_ROOT / "datasets" / "processed"

CLASSIFIER_WEIGHTS = WEIGHTS_DIR / "crack_cnn.pt"
UNET_WEIGHTS = WEIGHTS_DIR / "unet_deepcrack.pt"
YOLO_WEIGHTS = WEIGHTS_DIR / "yolo_rdd.pt"

DEEPCRACK_ROOT = DATASETS_RAW / "deepcrack" / "extracted"
RDD_TRAIN_IMAGES = DATASETS_RAW / "rdd2022_czech" / "extracted" / "Czech" / "train" / "images"
RDD_TRAIN_XML = DATASETS_RAW / "rdd2022_czech" / "extracted" / "Czech" / "train" / "annotations" / "xmls"
CFD_ROOT = DATASETS_RAW / "cfd"
YOLO_DATASET_DIR = DATASETS_PROCESSED / "rdd2022_yolo"


def ensure_model_dirs() -> None:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
