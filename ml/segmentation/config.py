"""InfraScan Crack Segmentation Configuration.

Centralized configuration for U-Net and U-Net++ crack segmentation on Crack500
and CFD (DeepCrack/CFD external evaluation), including training hyperparameters,
data augmentation, loss weights, evaluation thresholds, and Kaggle/Colab paths.
"""

from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Dataset & Manifest Configurations
# ---------------------------------------------------------------------------
DATASET_NAMES: List[str] = ["crack500", "cfd"]

# Expected local manifest paths
LOCAL_RAW_MANIFESTS: Dict[str, str] = {
    "crack500": r"data\processed\manifests\crack500.csv",
    "cfd": r"data\processed\manifests\cfd.csv",
}

# Relative manifest paths inside packaged archives / Kaggle working dir
RELATIVE_MANIFESTS: Dict[str, str] = {
    "crack500": "manifests_seg/crack500.csv",
    "cfd": "manifests_seg/cfd.csv",
}

# ---------------------------------------------------------------------------
# Preprocessing & Augmentation Settings
# ---------------------------------------------------------------------------
IMAGE_SIZE_TRAIN: int = 384          # Random 384x384 crop during training
PAD_MULTIPLE_EVAL: int = 32         # Pad to multiple of 32 for U-Net architectures during val/test
JITTER_FACTOR: float = 0.20          # +-20% brightness and contrast jitter

# Standard ImageNet normalization statistics
IMAGENET_MEAN: Tuple[float, float, float] = (0.485, 0.456, 0.406)
IMAGENET_STD: Tuple[float, float, float] = (0.229, 0.224, 0.225)

# Mask Thresholding
MASK_POSITIVE_THRESHOLD: float = 0.0  # Pixel is crack when mask value > 0

# ---------------------------------------------------------------------------
# Model Architecture Settings
# ---------------------------------------------------------------------------
SUPPORTED_MODELS: List[str] = ["unet", "unetplusplus"]
ENCODER_BACKBONE: str = "resnet34"
ENCODER_WEIGHTS: str = "imagenet"
IN_CHANNELS: int = 3
NUM_CLASSES: int = 1  # Binary segmentation (single output logit)

# ---------------------------------------------------------------------------
# Training Hyperparameters
# ---------------------------------------------------------------------------
RANDOM_SEED: int = 42
BATCH_SIZE: int = 8
MAX_EPOCHS: int = 40
EARLY_STOPPING_PATIENCE: int = 8     # Monitored on validation Dice score
LR_ENCODER: float = 3e-4             # AdamW backbone learning rate
LR_DECODER: float = 1e-3             # AdamW head/decoder learning rate
WEIGHT_DECAY: float = 1e-4
COSINE_ETA_MIN: float = 1e-6
MIXED_PRECISION: bool = True         # torch.cuda.amp.autocast
WORKERS: int = 2

# Debug Mode
DEBUG_TRAIN_SAMPLES: int = 200
DEBUG_VAL_SAMPLES: int = 50
DEBUG_EPOCHS: int = 1

# ---------------------------------------------------------------------------
# Validation Threshold Sweep Settings
# ---------------------------------------------------------------------------
SWEEP_THRESH_START: float = 0.10
SWEEP_THRESH_END: float = 0.90
SWEEP_THRESH_STEP: float = 0.05
DEFAULT_THRESHOLD: float = 0.50

# ---------------------------------------------------------------------------
# Evaluation & Diagnostics Settings
# ---------------------------------------------------------------------------
BOUNDARY_TOLERANCE_PX: int = 3       # Boundary F1 evaluation tolerance in pixels
BOOTSTRAP_RESAMPLES: int = 500
BOOTSTRAP_SEED: int = 42

# Crack width binning (half-width from distance transform * 2)
WIDTH_THIN_MAX: float = 5.0          # < 5.0 px = thin
WIDTH_MED_MAX: float = 15.0          # 5.0 to 15.0 px = medium, > 15.0 px = thick

# Inference speed benchmark settings
SPEED_WARMUP_RUNS: int = 10
SPEED_TIMED_RUNS: int = 200

# Number of panels to save
NUM_VISUALIZATION_PANELS: int = 24

# Single-run guard flag: set to True only to overwrite existing test results
FORCE_RERUN: bool = False

# ---------------------------------------------------------------------------
# Environment Paths (Kaggle Default Layout)
# ---------------------------------------------------------------------------
KAGGLE_INPUT_DIR: str = r"/kaggle/input"
KAGGLE_WORKING_DIR: str = r"/kaggle/working"
KAGGLE_DATA_DIR: str = r"/kaggle/working/data"
KAGGLE_MODELS_DIR: str = r"/kaggle/working/models/segmentation"
KAGGLE_RESULTS_ZIP: str = r"/kaggle/working/segmentation_results.zip"

