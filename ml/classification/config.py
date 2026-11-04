"""
Configuration parameters for InfraScan baseline crack/no-crack image classifier.
All hyperparameters, preprocessing flags, augmentation settings, and paths in one place.
"""

from dataclasses import dataclass
from pathlib import Path


# ==============================================================================
# REPRODUCIBILITY & SYSTEM SETTINGS
# ==============================================================================
RANDOM_SEED: int = 42

# Label definitions: 1 = crack, 0 = no crack
LABEL_CRACK: int = 1
LABEL_NO_CRACK: int = 0
LABEL_MAPPING = {
    "cracked": LABEL_CRACK,
    "uncracked": LABEL_NO_CRACK,
    "positive": LABEL_CRACK,
    "negative": LABEL_NO_CRACK,
    1: LABEL_CRACK,
    0: LABEL_NO_CRACK,
}
CLASS_NAMES = {
    LABEL_NO_CRACK: "uncracked",
    LABEL_CRACK: "cracked",
}


# ==============================================================================
# PREPROCESSING & AUGMENTATION
# ==============================================================================
# Shared preprocessing module settings
MODEL_INPUT_SIZE: int = 224
NORMALIZE_MODE: str = "imagenet"  # Uses standard ImageNet mean and std
USE_CLAHE: bool = True            # Maps to ENABLE_CONTRAST in PreprocessConfig

# Train-only augmentation settings (applied before preprocess())
# Note: No heavy cropping to preserve thin cracks
AUG_HFLIP_PROB: float = 0.5
AUG_VFLIP_PROB: float = 0.5
AUG_ROT90_PROB: float = 0.5
AUG_BRIGHTNESS_JITTER: float = 0.20  # +/- 20%
AUG_CONTRAST_JITTER: float = 0.20    # +/- 20%


# ==============================================================================
# MODEL ARCHITECTURE
# ==============================================================================
MODEL_NAME: str = "resnet50"
NUM_CLASSES: int = 1  # Binary classification with single raw logit output


# ==============================================================================
# TRAINING HYPERPARAMETERS
# ==============================================================================
BATCH_SIZE: int = 64
NUM_WORKERS: int = 2

# Phase 1: Transfer learning warmup (backbone frozen, custom linear head only)
PHASE1_LR: float = 1e-3
PHASE1_EPOCHS: int = 2

# Phase 2: Full fine-tuning (all layers unfrozen)
PHASE2_LR: float = 1e-4
PHASE2_WEIGHT_DECAY: float = 1e-4
PHASE2_MAX_EPOCHS: int = 12
EARLY_STOPPING_PATIENCE: int = 3  # Patience on val F1 of crack class (tie-break: val recall)

# Optimization & Precision
OPTIMIZER: str = "adamw"
USE_AMP: bool = True  # Mixed precision (torch.amp.autocast + GradScaler)


# ==============================================================================
# POST-TRAINING THRESHOLD OPTIMIZATION
# ==============================================================================
# Chosen on validation split only: max F1 subject to recall >= 0.90 (fallback: max F1)
MIN_RECALL_CONSTRAINT: float = 0.90
NUM_THRESHOLD_STEPS: int = 100


# ==============================================================================
# DEBUG & SMOKE TEST MODES
# ==============================================================================
# Quick testing on GPU (Colab debug mode)
DEBUG_TRAIN_SAMPLES: int = 2000
DEBUG_VAL_SAMPLES: int = 500
DEBUG_PHASE1_EPOCHS: int = 1
DEBUG_PHASE2_EPOCHS: int = 1

# Local CPU smoke test settings
SMOKE_TRAIN_SAMPLES: int = 64
SMOKE_VAL_SAMPLES: int = 32
SMOKE_PHASE1_EPOCHS: int = 1
SMOKE_PHASE2_EPOCHS: int = 1
SMOKE_BATCH_SIZE: int = 16

