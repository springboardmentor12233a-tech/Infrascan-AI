"""
InfraScan Baseline Crack/No-Crack Image Classifier.
ResNet-50 Transfer Learning Pipeline with 2-Phase Training, Mixed Precision,
Validation Threshold Optimization, and Model Artifact Generation.

Optimized for Google Colab (T4 GPU) and local CPU smoke testing.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import torchvision
from torchvision import models

# Import shared preprocessing pipeline
# Ensure backend directory or root is on sys.path
_current_dir = Path(__file__).resolve().parent
_repo_infrascan = _current_dir.parents[1]  # infrascan/
_backend_dir = _repo_infrascan / "backend"

if _backend_dir.exists() and str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
if str(_repo_infrascan) not in sys.path:
    sys.path.insert(0, str(_repo_infrascan))

try:
    from app.ai.preprocessing import preprocess, PreprocessConfig
except (ImportError, ModuleNotFoundError):
    # Graceful shim for app.config if pydantic_settings or backend config is not installed
    import types
    if "app" not in sys.modules:
        app_mod = types.ModuleType("app")
        # If app folder exists in cwd or backend, set path
        for candidate in [_backend_dir / "app", Path.cwd() / "app"]:
            if candidate.exists():
                app_mod.__path__ = [str(candidate)]
                break
        sys.modules["app"] = app_mod
    if "app.config" not in sys.modules:
        config_mod = types.ModuleType("app.config")
        class _FallbackSettings:
            BLUR_THRESHOLD = 100.0
            BRIGHTNESS_MIN = 50.0
            BRIGHTNESS_MAX = 220.0
        config_mod.settings = _FallbackSettings()
        sys.modules["app.config"] = config_mod
    from app.ai.preprocessing import preprocess, PreprocessConfig

# Import local classification config
try:
    from ml.classification import config
except ImportError:
    try:
        from classification import config
    except ImportError:
        import config


# ==============================================================================
# REPRODUCIBILITY UTILITIES
# ==============================================================================
def set_seed(seed: int = config.RANDOM_SEED) -> None:
    """Seed Python, NumPy, PyTorch CPU & GPU generators for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def seed_worker(worker_id: int) -> None:
    """DataLoader worker initializer for deterministic sample ordering."""
    worker_seed = (torch.initial_seed() + worker_id) % (2**32)
    np.random.seed(worker_seed)
    random.seed(worker_seed)


# ==============================================================================
# 1. MANIFEST LOADER
# ==============================================================================
def _extract_relative_raw_path(original_path: str) -> str:
    """Extract path segment relative to data/raw from full Windows, POSIX, or already-relative path."""
    norm = str(original_path).replace("\\", "/").strip()
    if "data/raw/" in norm:
        return norm.split("data/raw/", 1)[1].lstrip("/")
    if "data\\raw\\" in str(original_path):
        return str(original_path).split("data\\raw\\", 1)[1].replace("\\", "/").lstrip("/")
    # If path is already relative (e.g. from colab manifests: concrete_crack_cls/Positive/00001.jpg):
    is_win_abs = len(norm) >= 2 and norm[1] == ":"
    if not is_win_abs and not norm.startswith("/"):
        return norm.lstrip("./")
    # If absolute path contains dataset prefix:
    for ds in ["concrete_crack_cls/", "sdnet2018/"]:
        if ds in norm:
            return norm[norm.index(ds):].lstrip("/")
    return os.path.basename(original_path)


def load_manifest(
    csv_path: Union[str, Path],
    data_root: Union[str, Path],
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load dataset manifest, remap image paths to data_root, map labels to binary (1=crack, 0=no crack),
    and split into train, val, and test dataframes.

    NOTE: The test split dataframe is returned for evaluation pipelines only; it is never
          used in model training, validation, or threshold tuning.
    """
    csv_path = Path(csv_path)
    data_root = Path(data_root)

    if not csv_path.exists():
        raise FileNotFoundError(f"Manifest CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # Remap paths to data_root
    root_str = str(data_root).replace("\\", "/").rstrip("/")

    def remap(p: str) -> str:
        rel = _extract_relative_raw_path(p)
        if root_str.startswith("/") or ("/" in root_str and ":" not in root_str):
            return f"{root_str}/{rel}"
        return str(Path(data_root) / Path(rel))

    df["path"] = df["path"].apply(remap)

    # Label mapping (1 = crack, 0 = no crack)
    print(f"[load_manifest] Label mapping defined: {config.LABEL_MAPPING}")
    original_labels = df["label"].astype(str).str.lower()
    df["label"] = original_labels.map(config.LABEL_MAPPING)

    if df["label"].isnull().any():
        unmapped = original_labels[df["label"].isnull()].unique()
        raise ValueError(f"Unmapped label values encountered in manifest: {unmapped}")

    df["label"] = df["label"].astype(int)

    # Verify split column
    if "split" not in df.columns:
        raise KeyError(f"Manifest missing required 'split' column: {csv_path}")

    train_df = df[df["split"] == "train"].copy().reset_index(drop=True)
    val_df = df[df["split"] == "val"].copy().reset_index(drop=True)
    test_df = df[df["split"] == "test"].copy().reset_index(drop=True)

    print(f"[load_manifest] Successfully loaded manifest: {csv_path.name}")
    print(f"  - Total entries: {len(df):,}")
    print(
        f"  - Train split:   {len(train_df):,} | Cracks: {(train_df['label'] == 1).sum():,}, "
        f"No-cracks: {(train_df['label'] == 0).sum():,}"
    )
    print(
        f"  - Val split:     {len(val_df):,} | Cracks: {(val_df['label'] == 1).sum():,}, "
        f"No-cracks: {(val_df['label'] == 0).sum():,}"
    )
    print(
        f"  - Test split:    {len(test_df):,} | Cracks: {(test_df['label'] == 1).sum():,}, "
        f"No-cracks: {(test_df['label'] == 0).sum():,}"
    )

    return train_df, val_df, test_df


# ==============================================================================
# 2. DATASET CLASS WITH AUGMENTATION & SHARED PREPROCESSING
# ==============================================================================
class CrackDataset(Dataset):
    """
    Dataset class reading BGR images with OpenCV, applying train-only geometric
    and photometric augmentations (without heavy cropping), executing shared
    preprocess() from preprocessing.py, and returning (CHW float tensor, label float).
    """

    def __init__(
        self,
        df: pd.DataFrame,
        is_train: bool = False,
        use_clahe: bool = config.USE_CLAHE,
    ):
        self.df = df.reset_index(drop=True)
        self.is_train = is_train
        self.use_clahe = use_clahe
        self.preprocess_config = PreprocessConfig(
            model_input_size=config.MODEL_INPUT_SIZE,
            normalize_mode=config.NORMALIZE_MODE,
            enable_contrast=use_clahe,
            enable_denoise=False,
            enable_sharpen=False,
        )

    def __len__(self) -> int:
        return len(self.df)

    def _apply_train_augmentation(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Train-only augmentations applied BEFORE preprocess():
        - Random horizontal flip (p=0.5)
        - Random vertical flip (p=0.5)
        - Random 90-degree rotations (0, 90, 180, 270 deg)
        - Brightness / contrast jitter of +/- 20%
        No heavy cropping is applied to ensure fine, thin cracks are never cut away.
        """
        # 1. Random horizontal flip
        if random.random() < config.AUG_HFLIP_PROB:
            img_bgr = cv2.flip(img_bgr, 1)

        # 2. Random vertical flip
        if random.random() < config.AUG_VFLIP_PROB:
            img_bgr = cv2.flip(img_bgr, 0)

        # 3. Random 90-degree rotation
        if random.random() < config.AUG_ROT90_PROB:
            rot_code = random.choice([
                cv2.ROTATE_90_CLOCKWISE,
                cv2.ROTATE_180,
                cv2.ROTATE_90_COUNTERCLOCKWISE,
            ])
            img_bgr = cv2.rotate(img_bgr, rot_code)

        # 4. Brightness & contrast jitter (+/- 20%)
        alpha = 1.0 + random.uniform(-config.AUG_CONTRAST_JITTER, config.AUG_CONTRAST_JITTER)
        beta = random.uniform(-config.AUG_BRIGHTNESS_JITTER, config.AUG_BRIGHTNESS_JITTER) * 255.0
        img_bgr = cv2.convertScaleAbs(img_bgr, alpha=alpha, beta=beta)

        return img_bgr

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        row = self.df.iloc[idx]
        img_path = row["path"]

        # Read image using OpenCV (BGR format)
        img_bgr = cv2.imread(img_path)
        if img_bgr is None:
            raise FileNotFoundError(f"Failed to read image at path: {img_path}")

        # Apply train-only augmentation BEFORE preprocess()
        if self.is_train:
            img_bgr = self._apply_train_augmentation(img_bgr)

        # Run SHARED preprocess() function from backend/app/ai/preprocessing.py
        result = preprocess(img_bgr, config=self.preprocess_config)

        # model_input is float32 (H, W, C) normalized with ImageNet stats
        # Convert to PyTorch (C, H, W) float tensor
        tensor = torch.from_numpy(result.model_input).permute(2, 0, 1).float()
        label = torch.tensor(row["label"], dtype=torch.float32)

        return tensor, label


# ==============================================================================
# 3. MODEL BUILDER
# ==============================================================================
def build_model(pretrained: bool = True) -> nn.Module:
    """
    Construct torchvision ResNet-50 with ImageNet pretrained weights,
    replacing the final fully-connected layer with 1 output logit.
    """
    weights = models.ResNet50_Weights.DEFAULT if pretrained else None
    model = models.resnet50(weights=weights)

    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, config.NUM_CLASSES)

    return model


# ==============================================================================
# 4. EVALUATION & METRICS COMPUTATION
# ==============================================================================
@torch.no_grad()
def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    threshold: float = 0.5,
) -> Tuple[Dict[str, float], np.ndarray, np.ndarray]:
    """
    Evaluate model over validation dataloader.
    Returns:
        metrics: dict of val_loss, val_acc, val_precision, val_recall, val_f1, val_auc
        all_targets: ground truth binary labels
        all_probs: predicted probabilities for the crack class (1)
    """
    model.eval()
    total_loss = 0.0
    total_samples = 0
    all_targets = []
    all_probs = []

    for images, targets in dataloader:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        logits = model(images).squeeze(-1)
        loss = criterion(logits, targets)

        probs = torch.sigmoid(logits)

        total_loss += loss.item() * targets.size(0)
        total_samples += targets.size(0)

        all_targets.append(targets.cpu().numpy())
        all_probs.append(probs.cpu().numpy())

    all_targets = np.concatenate(all_targets)
    all_probs = np.concatenate(all_probs)

    avg_loss = total_loss / max(total_samples, 1)
    preds = (all_probs >= threshold).astype(int)

    acc = float(accuracy_score(all_targets, preds))
    prec = float(precision_score(all_targets, preds, zero_division=0))
    rec = float(recall_score(all_targets, preds, zero_division=0))
    f1 = float(f1_score(all_targets, preds, zero_division=0))

    try:
        auc = float(roc_auc_score(all_targets, all_probs))
    except Exception:
        auc = 0.5  # In case validation batch contains only single class

    metrics = {
        "loss": avg_loss,
        "acc": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "auc": auc,
    }
    return metrics, all_targets, all_probs


def find_optimal_threshold(
    targets: np.ndarray,
    probs: np.ndarray,
    min_recall: float = config.MIN_RECALL_CONSTRAINT,
) -> Tuple[float, float, float, float]:
    """
    On the validation set ONLY, select the decision threshold that maximizes F1 score
    subject to recall >= min_recall (0.90). If no threshold achieves recall >= 0.90,
    the unconstrained F1-maximizing threshold is chosen.

    Returns (best_threshold, best_f1, recall_at_best, precision_at_best).
    """
    thresholds = np.linspace(0.01, 0.99, config.NUM_THRESHOLD_STEPS)

    best_thresh = 0.5
    best_f1 = -1.0
    best_rec = 0.0
    best_prec = 0.0

    # Pass 1: Try to find maximum F1 satisfying recall >= min_recall
    candidates = []
    for th in thresholds:
        preds = (probs >= th).astype(int)
        rec = float(recall_score(targets, preds, zero_division=0))
        prec = float(precision_score(targets, preds, zero_division=0))
        f1 = float(f1_score(targets, preds, zero_division=0))

        if rec >= min_recall:
            candidates.append((f1, rec, prec, th))

    if candidates:
        # Sort by F1 descending, tie-break by recall descending
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best_f1, best_rec, best_prec, best_thresh = candidates[0]
    else:
        # Pass 2 Fallback: Maximize F1 across all thresholds
        for th in thresholds:
            preds = (probs >= th).astype(int)
            rec = float(recall_score(targets, preds, zero_division=0))
            prec = float(precision_score(targets, preds, zero_division=0))
            f1 = float(f1_score(targets, preds, zero_division=0))
            if f1 > best_f1 or (f1 == best_f1 and rec > best_rec):
                best_f1 = f1
                best_rec = rec
                best_prec = prec
                best_thresh = th

    return float(best_thresh), float(best_f1), float(best_rec), float(best_prec)


# ==============================================================================
# 5. TRAINING ENGINE
# ==============================================================================
def train(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    output_dir: Union[str, Path],
    dataset_name: str = "dataset",
    manifest_name: str = "manifest.csv",
    debug: bool = False,
    smoke_test: bool = False,
    device: Optional[torch.device] = None,
    use_clahe: bool = config.USE_CLAHE,
) -> Dict[str, Any]:
    """
    Execute 2-Phase ResNet-50 transfer learning:
    - BCEWithLogitsLoss with pos_weight = (no-crack count / crack count) from TRAIN split only.
    - AdamW optimizer, mixed precision (autocast + GradScaler).
    - Phase 1: backbone frozen, custom head only.
    - Phase 2: everything unfrozen with cosine learning rate schedule and early stopping.
    - Logs history.csv, saves last.pth and best.pth (with resume support).
    - Validates optimal decision threshold, generates training curves, confusion matrix,
      predictions CSV, and model_card.json.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    set_seed(config.RANDOM_SEED)

    # Select device
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n{'='*70}")
    print(f"STARTING CLASSIFIER TRAINING: {dataset_name.upper()}")
    print(f"Device: {device} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")
    print(f"Output directory: {output_dir}")
    print(f"{'='*70}\n")

    # Debug / Smoke test subset slicing
    if smoke_test:
        print(f"[Mode] SMOKE TEST active: using {config.SMOKE_TRAIN_SAMPLES} train and {config.SMOKE_VAL_SAMPLES} val samples.")
        train_df = train_df.sample(n=min(config.SMOKE_TRAIN_SAMPLES, len(train_df)), random_state=config.RANDOM_SEED).reset_index(drop=True)
        val_df = val_df.sample(n=min(config.SMOKE_VAL_SAMPLES, len(val_df)), random_state=config.RANDOM_SEED).reset_index(drop=True)
        batch_size = config.SMOKE_BATCH_SIZE
        phase1_epochs = config.SMOKE_PHASE1_EPOCHS
        phase2_max_epochs = config.SMOKE_PHASE2_EPOCHS
        patience = 2
    elif debug:
        print(f"[Mode] DEBUG active: using {config.DEBUG_TRAIN_SAMPLES} train and {config.DEBUG_VAL_SAMPLES} val samples.")
        train_df = train_df.sample(n=min(config.DEBUG_TRAIN_SAMPLES, len(train_df)), random_state=config.RANDOM_SEED).reset_index(drop=True)
        val_df = val_df.sample(n=min(config.DEBUG_VAL_SAMPLES, len(val_df)), random_state=config.RANDOM_SEED).reset_index(drop=True)
        batch_size = config.BATCH_SIZE
        phase1_epochs = config.DEBUG_PHASE1_EPOCHS
        phase2_max_epochs = config.DEBUG_PHASE2_EPOCHS
        patience = 2
    else:
        batch_size = config.BATCH_SIZE
        phase1_epochs = config.PHASE1_EPOCHS
        phase2_max_epochs = config.PHASE2_MAX_EPOCHS
        patience = config.EARLY_STOPPING_PATIENCE

    # Compute pos_weight = (no-crack count / crack count) from TRAIN split only
    num_no_crack = int((train_df["label"] == 0).sum())
    num_crack = int((train_df["label"] == 1).sum())
    pos_weight_val = float(num_no_crack) / max(float(num_crack), 1.0)
    pos_weight = torch.tensor([pos_weight_val], device=device)
    print(f"[Loss Config] Train split class balance:")
    print(f"  - No-crack (0): {num_no_crack:,}")
    print(f"  - Crack (1):    {num_crack:,}")
    print(f"  - Calculated pos_weight: {pos_weight_val:.4f}\n")

    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    # Datasets and DataLoaders
    train_dataset = CrackDataset(train_df, is_train=True, use_clahe=use_clahe)
    val_dataset = CrackDataset(val_df, is_train=False, use_clahe=use_clahe)

    g = torch.Generator()
    g.manual_seed(config.RANDOM_SEED)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=config.NUM_WORKERS if device.type == "cuda" else 0,
        worker_init_fn=seed_worker,
        generator=g,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=config.NUM_WORKERS if device.type == "cuda" else 0,
        worker_init_fn=seed_worker,
        pin_memory=(device.type == "cuda"),
    )

    # Build model
    model = build_model(pretrained=True).to(device)

    # Mixed precision setup
    use_amp = (device.type == "cuda") and config.USE_AMP
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    # Resume support
    last_checkpoint_path = output_dir / "last.pth"
    best_checkpoint_path = output_dir / "best.pth"
    history_csv_path = output_dir / "history.csv"

    history: List[Dict[str, Any]] = []
    start_epoch = 1
    best_val_f1 = -1.0
    best_val_rec = -1.0
    best_epoch = 0

    if last_checkpoint_path.exists():
        print(f"[Resume] Found existing checkpoint at {last_checkpoint_path}. Resuming training...")
        checkpoint = torch.load(last_checkpoint_path, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        start_epoch = checkpoint["epoch"] + 1
        best_val_f1 = checkpoint.get("best_metric", -1.0)
        history = checkpoint.get("history", [])
        if "scaler_state_dict" in checkpoint and use_amp:
            scaler.load_state_dict(checkpoint["scaler_state_dict"])
        print(f"[Resume] Resumed at epoch {start_epoch}, prior best F1: {best_val_f1:.4f}")

    total_epochs = phase1_epochs + phase2_max_epochs
    epochs_no_improve = 0

    # Main training loop across epochs
    for current_epoch in range(start_epoch, total_epochs + 1):
        epoch_start_time = time.time()
        in_phase1 = current_epoch <= phase1_epochs

        # Configure phase parameters
        if in_phase1:
            phase_name = "Phase 1 (Backbone Frozen)"
            for name, param in model.named_parameters():
                param.requires_grad = name.startswith("fc.")
            current_lr = config.PHASE1_LR
            optimizer = torch.optim.AdamW(model.fc.parameters(), lr=current_lr)
            scheduler = None
        else:
            phase_name = "Phase 2 (Full Fine-Tuning)"
            for param in model.parameters():
                param.requires_grad = True
            current_lr = config.PHASE2_LR
            optimizer = torch.optim.AdamW(
                model.parameters(),
                lr=current_lr,
                weight_decay=config.PHASE2_WEIGHT_DECAY,
            )
            # Cosine annealing over the remaining phase 2 epochs
            phase2_step = current_epoch - phase1_epochs
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer,
                T_max=phase2_max_epochs,
                eta_min=1e-6,
            )
            # Advance scheduler to current step if resuming
            for _ in range(phase2_step - 1):
                scheduler.step()

        # Training pass
        model.train()
        train_loss = 0.0
        train_samples = 0

        for images, targets in train_loader:
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)

            optimizer.zero_grad()

            with torch.amp.autocast("cuda", enabled=use_amp):
                logits = model(images).squeeze(-1)
                loss = criterion(logits, targets)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item() * targets.size(0)
            train_samples += targets.size(0)

        if scheduler is not None:
            scheduler.step()

        epoch_train_loss = train_loss / max(train_samples, 1)

        # Validation pass
        val_metrics, _, _ = evaluate(model, val_loader, criterion, device, threshold=0.5)
        epoch_time = time.time() - epoch_start_time

        epoch_record = {
            "epoch": current_epoch,
            "phase": phase_name,
            "lr": optimizer.param_groups[0]["lr"],
            "train_loss": round(epoch_train_loss, 4),
            "val_loss": round(val_metrics["loss"], 4),
            "val_acc": round(val_metrics["acc"], 4),
            "val_precision": round(val_metrics["precision"], 4),
            "val_recall": round(val_metrics["recall"], 4),
            "val_f1": round(val_metrics["f1"], 4),
            "val_auc": round(val_metrics["auc"], 4),
            "duration_sec": round(epoch_time, 1),
        }
        history.append(epoch_record)

        print(
            f"Epoch {current_epoch:02d}/{total_epochs:02d} [{phase_name}] ({epoch_time:.1f}s) | "
            f"Train Loss: {epoch_train_loss:.4f} | Val Loss: {val_metrics['loss']:.4f} | "
            f"Val F1: {val_metrics['f1']:.4f} | Val Rec: {val_metrics['recall']:.4f} | "
            f"Val Prec: {val_metrics['precision']:.4f} | Val AUC: {val_metrics['auc']:.4f}"
        )

        # Check for improvement (metric = Val F1, tie-breaker = Val Recall)
        cur_f1 = val_metrics["f1"]
        cur_rec = val_metrics["recall"]
        is_best = (cur_f1 > best_val_f1) or (cur_f1 == best_val_f1 and cur_rec > best_val_rec)

        if is_best:
            best_val_f1 = cur_f1
            best_val_rec = cur_rec
            best_epoch = current_epoch
            epochs_no_improve = 0
            torch.save({
                "epoch": current_epoch,
                "model_state_dict": model.state_dict(),
                "best_val_f1": best_val_f1,
                "best_val_recall": best_val_rec,
                "dataset_name": dataset_name,
            }, best_checkpoint_path)
            print(f"  [*] Best model saved to {best_checkpoint_path} (F1: {best_val_f1:.4f})")
        else:
            if not in_phase1:
                epochs_no_improve += 1

        # Save last checkpoint after EVERY epoch
        torch.save({
            "epoch": current_epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
            "scaler_state_dict": scaler.state_dict() if use_amp else None,
            "best_metric": best_val_f1,
            "history": history,
        }, last_checkpoint_path)

        # Save history.csv after each epoch
        pd.DataFrame(history).to_csv(history_csv_path, index=False)

        # Phase 2 early stopping
        if (not in_phase1) and (epochs_no_improve >= patience):
            print(f"\n[Early Stopping] No improvement in validation F1 for {patience} consecutive epochs. Stopping Phase 2.")
            break

    # ==========================================================================
    # 6. POST-TRAINING VALIDATION & THRESHOLD OPTIMIZATION
    # ==========================================================================
    print(f"\n{'='*70}")
    print("POST-TRAINING VALIDATION & THRESHOLD OPTIMIZATION")
    print(f"{'='*70}")

    # Load best checkpoint for final evaluation
    if best_checkpoint_path.exists():
        best_ckpt = torch.load(best_checkpoint_path, map_location=device)
        model.load_state_dict(best_ckpt["model_state_dict"])
        print(f"[Model] Evaluated using best checkpoint from epoch {best_epoch} (F1: {best_val_f1:.4f})")

    # Run inference across VALIDATION set ONLY
    final_metrics_default, val_targets, val_probs = evaluate(
        model, val_loader, criterion, device, threshold=0.5
    )

    # Choose optimal threshold (max F1 subject to recall >= 0.90)
    opt_thresh, opt_f1, opt_rec, opt_prec = find_optimal_threshold(
        val_targets, val_probs, min_recall=config.MIN_RECALL_CONSTRAINT
    )
    print(f"\nOptimal Decision Threshold (Validation Split Only):")
    print(f"  - Selected Threshold: {opt_thresh:.4f}")
    print(f"  - Val Recall:         {opt_rec:.4f} (Constraint: >= {config.MIN_RECALL_CONSTRAINT:.2f})")
    print(f"  - Val Precision:      {opt_prec:.4f}")
    print(f"  - Val F1 Score:       {opt_f1:.4f}")

    # 1. Save val_predictions.csv (path, label, probability)
    val_preds_df = pd.DataFrame({
        "path": val_df["path"],
        "label": val_targets.astype(int),
        "probability": np.round(val_probs, 6),
    })
    val_preds_path = output_dir / "val_predictions.csv"
    val_preds_df.to_csv(val_preds_path, index=False)
    print(f"[Artifact] Saved validation predictions: {val_preds_path}")

    # 2. Save training curves PNG (train/val loss, val F1)
    curves_path = output_dir / "training_curves.png"
    hist_df = pd.DataFrame(history)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax1.plot(hist_df["epoch"], hist_df["train_loss"], label="Train Loss", marker="o", color="#1f77b4")
    ax1.plot(hist_df["epoch"], hist_df["val_loss"], label="Val Loss", marker="s", color="#ff7f0e")
    ax1.set_title(f"{dataset_name} - Loss Curves")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("BCE Loss")
    ax1.legend()
    ax1.grid(True, linestyle="--", alpha=0.6)

    ax2.plot(hist_df["epoch"], hist_df["val_f1"], label="Val F1", marker="^", color="#2ca02c")
    ax2.plot(hist_df["epoch"], hist_df["val_recall"], label="Val Recall", linestyle="--", color="#d62728")
    ax2.set_title(f"{dataset_name} - Validation F1 & Recall")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Score")
    ax2.legend()
    ax2.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    fig.savefig(curves_path, dpi=150)
    plt.close(fig)
    print(f"[Artifact] Saved training curves: {curves_path}")

    # 3. Save confusion matrix PNG at chosen threshold
    opt_preds = (val_probs >= opt_thresh).astype(int)
    cm = confusion_matrix(val_targets, opt_preds)
    cm_path = output_dir / "val_confusion_matrix.png"

    fig_cm, ax_cm = plt.subplots(figsize=(6, 5))
    im = ax_cm.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax_cm.figure.colorbar(im, ax=ax_cm)
    classes = ["No Crack (0)", "Crack (1)"]
    ax_cm.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=classes,
        yticklabels=classes,
        title=f"Confusion Matrix (Thresh = {opt_thresh:.2f})\n{dataset_name}",
        ylabel="True Label",
        xlabel="Predicted Label",
    )
    thresh_val = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax_cm.text(
                j, i, f"{cm[i, j]:,}",
                ha="center", va="center",
                color="white" if cm[i, j] > thresh_val else "black",
                fontweight="bold"
            )
    plt.tight_layout()
    fig_cm.savefig(cm_path, dpi=150)
    plt.close(fig_cm)
    print(f"[Artifact] Saved confusion matrix: {cm_path}")

    # 4. Save model_card.json
    model_card = {
        "model_name": config.MODEL_NAME,
        "dataset": dataset_name,
        "manifest_name": manifest_name,
        "class_mapping": config.LABEL_MAPPING,
        "image_size": config.MODEL_INPUT_SIZE,
        "normalize_mode": config.NORMALIZE_MODE,
        "clahe_enabled": use_clahe,
        "chosen_threshold": round(opt_thresh, 4),
        "validation_metrics_at_threshold": {
            "f1_score": round(opt_f1, 4),
            "recall": round(opt_rec, 4),
            "precision": round(opt_prec, 4),
            "accuracy": round(float(accuracy_score(val_targets, opt_preds)), 4),
            "auc_roc": round(final_metrics_default["auc"], 4),
        },
        "seed": config.RANDOM_SEED,
        "best_epoch": best_epoch,
        "epochs_run": len(history),
        "train_samples": len(train_df),
        "val_samples": len(val_df),
        "pos_weight": round(pos_weight_val, 4),
        "torch_version": torch.__version__,
        "torchvision_version": torchvision.__version__,
        "date": datetime.now().isoformat(),
    }
    model_card_path = output_dir / "model_card.json"
    with open(model_card_path, "w", encoding="utf-8") as f:
        json.dump(model_card, f, indent=2)
    print(f"[Artifact] Saved model card: {model_card_path}")

    print(f"\n{'='*70}")
    print(f"TRAINING COMPLETE FOR {dataset_name.upper()}")
    print(f"Best Epoch: {best_epoch} | Best Val F1: {best_val_f1:.4f} | Optimal Threshold: {opt_thresh:.4f}")
    print(f"{'='*70}\n")

    return {
        "best_epoch": best_epoch,
        "best_val_f1": best_val_f1,
        "optimal_threshold": opt_thresh,
        "model_card": model_card,
    }


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train InfraScan ResNet-50 Crack Classifier.")
    parser.add_argument("--manifest", type=str, required=True, help="Path to manifest CSV.")
    parser.add_argument("--data_root", type=str, required=True, help="Root folder of raw images.")
    parser.add_argument("--output_dir", type=str, required=True, help="Destination folder for artifacts.")
    parser.add_argument("--dataset_name", type=str, default="dataset", help="Descriptive name of the dataset.")
    parser.add_argument("--debug", action="store_true", help="Run 2,000 train / 500 val debug mode.")
    parser.add_argument("--smoke_test", action="store_true", help="Run 64 train / 32 val CPU smoke test.")
    parser.add_argument("--no_clahe", action="store_true", help="Disable CLAHE contrast enhancement.")
    args = parser.parse_args()

    train_df, val_df, _ = load_manifest(args.manifest, args.data_root)

    train(
        train_df=train_df,
        val_df=val_df,
        output_dir=args.output_dir,
        dataset_name=args.dataset_name,
        manifest_name=Path(args.manifest).name,
        debug=args.debug,
        smoke_test=args.smoke_test,
        use_clahe=not args.no_clahe,
    )

