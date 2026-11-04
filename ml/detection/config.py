"""InfraScan Road Damage Detection Configuration.

Centralized configuration for YOLO (Ultralytics) training, validation,
testing, benchmarking, and packaging on the RDD2022 dataset.
"""

from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Class Definitions (RDD2022 4-class subset)
# ---------------------------------------------------------------------------
CLASS_MAPPING: Dict[int, str] = {
    0: "D00",
    1: "D10",
    2: "D20",
    3: "D40",
}

CLASS_NAMES: Dict[int, str] = {
    0: "D00 longitudinal crack",
    1: "D10 transverse crack",
    2: "D20 alligator crack",
    3: "D40 pothole",
}

NUM_CLASSES: int = len(CLASS_NAMES)

# ---------------------------------------------------------------------------
# Dataset & Stratification Settings
# ---------------------------------------------------------------------------
DATASET_NAME: str = "rdd2022_yolo_small"
DATASET_SPLITS: Dict[str, int] = {
    "train": 8000,
    "val": 1500,
    "test": 1500,
}

COUNTRIES: List[str] = [
    "China_Drone",
    "China_MotorBike",
    "Czech",
    "India",
    "Japan",
    "Norway",
    "United_States",
]

# ---------------------------------------------------------------------------
# Training Hyperparameters
# ---------------------------------------------------------------------------
RANDOM_SEED: int = 42
IMAGE_SIZE: int = 640
EPOCHS: int = 40
BATCH_SIZE: int = 16
PATIENCE: int = 10
DETERMINISTIC: bool = True
WORKERS: int = 2
AMP: bool = True
COS_LR: bool = True
SAVE_PERIOD: int = -1  # Ultralytics default: only save last.pt and best.pt
FLIPUD: float = 0.0  # Road surface cracks are not vertically symmetrical

# Debug mode overrides
DEBUG_FRACTION: float = 0.1
DEBUG_EPOCHS: int = 1

# Models
MODELS: Dict[str, str] = {
    "yolov8s": "yolov8s.pt",
    "yolo11s": "yolo11s.pt",
}

# ---------------------------------------------------------------------------
# Evaluation & Benchmarking Settings
# ---------------------------------------------------------------------------
VAL_CONF: float = 0.001  # Standard low confidence for generating full PR curve
VAL_IOU: float = 0.6     # Standard IoU threshold for NMS / mAP calculation

# Single-run guard flag: set to True only to overwrite existing test results
FORCE_RERUN: bool = False

# Bootstrap settings
BOOTSTRAP_RESAMPLES: int = 500
BOOTSTRAP_SEED: int = 42

# Near-duplicate leakage check settings
DHASH_BITS: int = 64
DHASH_HAMMING_THRESHOLD: int = 2

# Inference speed benchmark settings
SPEED_WARMUP_RUNS: int = 10
SPEED_TIMED_RUNS: int = 200
SPEED_BATCH_SIZE: int = 16

# Visualization sample counts
VIS_NUM_GOOD: int = 8
VIS_NUM_FN: int = 8
VIS_NUM_FP: int = 8
VIS_TOTAL_SAMPLES: int = VIS_NUM_GOOD + VIS_NUM_FN + VIS_NUM_FP  # 24

# ---------------------------------------------------------------------------
# Colab & Google Drive Paths
# ---------------------------------------------------------------------------
COLAB_CONTENT_ROOT: str = r"/content"
COLAB_DATA_EXTRACT_DIR: str = r"/content/rdd2022_yolo_small"
COLAB_DRIVE_PROJECT_ROOT: str = r"/content/drive/MyDrive/infrascan"
COLAB_MODELS_DIR: str = r"/content/drive/MyDrive/infrascan/models/detection"
COLAB_DATA_ZIP_PATH: str = r"/content/drive/MyDrive/infrascan/data/rdd2022_yolo_small.zip"
COLAB_CODE_ZIP_PATH: str = r"/content/drive/MyDrive/infrascan/ml_code_detection.zip"

