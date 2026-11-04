"""InfraScan Crack Segmentation Training Pipeline.

Provides automated training for U-Net and U-Net++ crack segmentation models on
Crack500 using segmentation-models-pytorch (SMP) with ResNet-34 backbone:
- CrackSegDataset with deterministic augmentation for training and reflection padding for validation/testing.
- Combined BCEWithLogits and Dice loss with dual-rate AdamW optimization.
- Early stopping on validation Dice score and cosine annealing schedule.
- Post-training validation threshold sweep (0.1 to 0.9).
- Checkpoint resumption, run cards, and epoch history tracking.
"""

import datetime
import json
import os
import platform
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from ml.segmentation import config


def seed_everything(seed: int = config.RANDOM_SEED) -> None:
    """Set random seeds across random, numpy, and torch for strict reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


class CrackSegDataset(Dataset):
    """Dataset for crack segmentation with dual-mode transforms."""

    def __init__(
        self,
        manifest_df: pd.DataFrame,
        data_root: str = "",
        is_train: bool = False,
        crop_size: int = config.IMAGE_SIZE_TRAIN,
        jitter: float = config.JITTER_FACTOR,
    ):
        """Args:

        manifest_df: DataFrame with columns 'image_path', 'mask_path', 'split'.
        data_root: Root directory to prepend to relative paths.
        is_train: If True, applies random 384x384 crop and augmentations.
                  If False, pads image to a multiple of 32 using reflection.
        crop_size: Spatial crop dimensions for training.
        jitter: Brightness and contrast jitter fraction (+-20%).
        """
        self.df = manifest_df.reset_index(drop=True)
        self.data_root = Path(data_root) if data_root else None
        self.is_train = is_train
        self.crop_size = crop_size
        self.jitter = jitter

        self.mean = np.array(config.IMAGENET_MEAN, dtype=np.float32)
        self.std = np.array(config.IMAGENET_STD, dtype=np.float32)

    def __len__(self) -> int:
        return len(self.df)

    def _resolve_path(self, rel_or_abs: str) -> str:
        p = Path(rel_or_abs)
        if p.is_absolute() and p.exists():
            return str(p)
        if self.data_root:
            cand = self.data_root / rel_or_abs
            if cand.exists():
                return str(cand)
        return str(p)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, int, int, str]:
        row = self.df.iloc[idx]
        img_path = self._resolve_path(row["image_path"])
        mask_path = self._resolve_path(row["mask_path"])

        # Read image in RGB
        img_bgr = cv2.imread(img_path)
        if img_bgr is None:
            raise FileNotFoundError(f"Failed to read image at: {img_path}")
        img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)

        # Read mask as grayscale
        mask_gray = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask_gray is None:
            raise FileNotFoundError(f"Failed to read mask at: {mask_path}")
        # Convert mask: any pixel > 0 is crack (1.0), else 0.0
        mask = (mask_gray > config.MASK_POSITIVE_THRESHOLD).astype(np.float32)

        orig_h, orig_w = img.shape[:2]

        if self.is_train:
            # 1. Random 384x384 crop (pad with reflection if smaller)
            pad_h = max(0, self.crop_size - orig_h)
            pad_w = max(0, self.crop_size - orig_w)
            if pad_h > 0 or pad_w > 0:
                img = cv2.copyMakeBorder(img, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT_101)
                mask = cv2.copyMakeBorder(mask, 0, pad_h, 0, pad_w, cv2.BORDER_CONSTANT, value=0)

            cur_h, cur_w = img.shape[:2]
            y1 = random.randint(0, cur_h - self.crop_size)
            x1 = random.randint(0, cur_w - self.crop_size)
            img = img[y1 : y1 + self.crop_size, x1 : x1 + self.crop_size]
            mask = mask[y1 : y1 + self.crop_size, x1 : x1 + self.crop_size]

            # 2. Horizontal flip
            if random.random() < 0.5:
                img = np.fliplr(img).copy()
                mask = np.fliplr(mask).copy()

            # 3. Vertical flip
            if random.random() < 0.5:
                img = np.flipud(img).copy()
                mask = np.flipud(mask).copy()

            # 4. 90-degree rotation
            k = random.choice([0, 1, 2, 3])
            if k > 0:
                img = np.rot90(img, k).copy()
                mask = np.rot90(mask, k).copy()

            # 5. Brightness and contrast jitter (+- 20% on image only)
            alpha = random.uniform(1.0 - self.jitter, 1.0 + self.jitter)
            beta = random.uniform(-self.jitter, self.jitter) * 255.0
            img = np.clip(img * alpha + beta, 0.0, 255.0)

        else:
            # VAL/TEST: pad image (reflect) to multiple of 32
            pad_h = (config.PAD_MULTIPLE_EVAL - (orig_h % config.PAD_MULTIPLE_EVAL)) % config.PAD_MULTIPLE_EVAL
            pad_w = (config.PAD_MULTIPLE_EVAL - (orig_w % config.PAD_MULTIPLE_EVAL)) % config.PAD_MULTIPLE_EVAL
            if pad_h > 0 or pad_w > 0:
                img = cv2.copyMakeBorder(img, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT_101)
                mask = cv2.copyMakeBorder(mask, 0, pad_h, 0, pad_w, cv2.BORDER_CONSTANT, value=0)

        # ImageNet Normalization
        img = (img / 255.0 - self.mean) / self.std

        # Convert to torch tensors (Channels First)
        img_tensor = torch.from_numpy(img.transpose(2, 0, 1)).float()
        mask_tensor = torch.from_numpy(mask).unsqueeze(0).float()

        return img_tensor, mask_tensor, orig_h, orig_w, str(row["image_path"])


def build_model(
    model_name: str = "unet",
    encoder_name: str = config.ENCODER_BACKBONE,
    encoder_weights: str = config.ENCODER_WEIGHTS,
    in_channels: int = config.IN_CHANNELS,
    classes: int = config.NUM_CLASSES,
) -> nn.Module:
    """Build U-Net or U-Net++ segmentation architecture with ImageNet pretrained encoder."""
    try:
        import segmentation_models_pytorch as smp
    except ImportError as e:
        raise ImportError(
            "segmentation-models-pytorch is required. Install via 'pip install segmentation-models-pytorch'."
        ) from e

    model_key = model_name.lower().replace("-", "").replace("_", "").replace("+", "plus")
    if model_key in ["unet", "u_net"]:
        model = smp.Unet(
            encoder_name=encoder_name,
            encoder_weights=encoder_weights,
            in_channels=in_channels,
            classes=classes,
        )
    elif model_key in ["unetplusplus", "unetplus"]:
        model = smp.UnetPlusPlus(
            encoder_name=encoder_name,
            encoder_weights=encoder_weights,
            in_channels=in_channels,
            classes=classes,
        )
    else:
        raise ValueError(f"Unsupported model architecture '{model_name}'. Choose from: {config.SUPPORTED_MODELS}")

    return model


class CombinedBCEDiceLoss(nn.Module):
    """Combined binary cross-entropy with logits and soft Dice loss."""

    def __init__(self, bce_weight: float = 1.0, dice_weight: float = 1.0, smooth: float = 1.0):
        super().__init__()
        self.bce = nn.BCEWithLogitsLoss()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce_loss = self.bce(logits, targets)
        probs = torch.sigmoid(logits)

        # Flatten spatial dims: (B, H*W)
        p = probs.reshape(probs.size(0), -1)
        t = targets.reshape(targets.size(0), -1)

        intersection = (p * t).sum(dim=1)
        cardinality = p.sum(dim=1) + t.sum(dim=1)
        dice = (2.0 * intersection + self.smooth) / (cardinality + self.smooth)
        dice_loss = 1.0 - dice.mean()

        return self.bce_weight * bce_loss + self.dice_weight * dice_loss


def compute_batch_dice_iou(
    probs: torch.Tensor,
    targets: torch.Tensor,
    threshold: float = 0.5,
    smooth: float = 1e-7,
) -> Tuple[float, float]:
    """Compute mean Dice score and IoU over a batch of unpadded spatial masks."""
    preds = (probs >= threshold).float()
    p = preds.reshape(preds.size(0), -1)
    t = targets.reshape(targets.size(0), -1)

    intersection = (p * t).sum(dim=1)
    total_pred = p.sum(dim=1)
    total_target = t.sum(dim=1)
    union = total_pred + total_target - intersection

    dice = (2.0 * intersection + smooth) / (total_pred + total_target + smooth)
    iou = (intersection + smooth) / (union + smooth)

    return float(dice.mean().item()), float(iou.mean().item())


def sweep_validation_thresholds(
    model: nn.Module,
    val_loader: DataLoader,
    device: torch.device,
    thresholds: Optional[List[float]] = None,
) -> Tuple[float, pd.DataFrame]:
    """Sweep probability thresholds on the validation split and pick the threshold that maximizes Dice."""
    if thresholds is None:
        thresholds = [
            round(t, 2)
            for t in np.arange(
                config.SWEEP_THRESH_START,
                config.SWEEP_THRESH_END + 1e-4,
                config.SWEEP_THRESH_STEP,
            )
        ]

    model.eval()
    all_unpadded_probs: List[np.ndarray] = []
    all_unpadded_gts: List[np.ndarray] = []

    with torch.no_grad():
        for imgs, masks, orig_hs, orig_ws, _ in val_loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs = torch.sigmoid(logits).cpu().numpy()
            masks_np = masks.numpy()

            for i in range(len(orig_hs)):
                oh, ow = int(orig_hs[i]), int(orig_ws[i])
                all_unpadded_probs.append(probs[i, 0, :oh, :ow])
                all_unpadded_gts.append(masks_np[i, 0, :oh, :ow])

    sweep_records = []
    best_dice = -1.0
    best_threshold = config.DEFAULT_THRESHOLD

    for th in thresholds:
        dices = []
        ious = []
        precisions = []
        recalls = []

        for p_map, g_map in zip(all_unpadded_probs, all_unpadded_gts):
            pred_b = (p_map >= th).astype(np.float32)
            tp = float((pred_b * g_map).sum())
            fp = float((pred_b * (1.0 - g_map)).sum())
            fn = float(((1.0 - pred_b) * g_map).sum())

            # Skip metric calculation for entirely empty GT images in per-image mean
            if g_map.sum() > 0 or pred_b.sum() > 0:
                dice = (2.0 * tp + 1e-7) / (2.0 * tp + fp + fn + 1e-7)
                iou = (tp + 1e-7) / (tp + fp + fn + 1e-7)
                prec = (tp + 1e-7) / (tp + fp + 1e-7)
                rec = (tp + 1e-7) / (tp + fn + 1e-7)
                dices.append(dice)
                ious.append(iou)
                precisions.append(prec)
                recalls.append(rec)

        mean_dice = float(np.mean(dices)) if dices else 0.0
        mean_iou = float(np.mean(ious)) if ious else 0.0
        mean_prec = float(np.mean(precisions)) if precisions else 0.0
        mean_rec = float(np.mean(recalls)) if recalls else 0.0

        sweep_records.append({
            "threshold": th,
            "val_dice": round(mean_dice, 4),
            "val_iou": round(mean_iou, 4),
            "val_precision": round(mean_prec, 4),
            "val_recall": round(mean_rec, 4),
        })

        if mean_dice > best_dice:
            best_dice = mean_dice
            best_threshold = th

    sweep_df = pd.DataFrame(sweep_records)
    print(f"\n[THRESHOLD SWEEP] Optimal Validation Threshold: {best_threshold:.2f} (Val Dice: {best_dice:.4f})")
    return best_threshold, sweep_df


def train(
    model_name: str,
    manifest_csv: str,
    project_dir: str,
    run_name: str,
    data_root: str = "",
    debug: bool = False,
    epochs: Optional[int] = None,
    batch_size: Optional[int] = None,
    seed: int = config.RANDOM_SEED,
    device_str: str = "cuda:0",
) -> Dict[str, Any]:
    """Train a segmentation model (U-Net or U-Net++) with early stopping and run card logging."""
    seed_everything(seed)
    device = torch.device(device_str if torch.cuda.is_available() else "cpu")

    project_path = Path(project_dir)
    run_dir = project_path / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    best_pth = run_dir / "best.pth"
    last_pth = run_dir / "last.pth"
    history_csv = run_dir / "history.csv"
    run_card_path = run_dir / "run_card.json"
    sweep_csv_path = run_dir / "threshold_sweep_val.csv"

    # Read manifest
    df_manifest = pd.read_csv(manifest_csv)
    train_df = df_manifest[df_manifest["split"] == "train"].copy()
    val_df = df_manifest[df_manifest["split"] == "val"].copy()

    # Debug mode overrides
    if debug:
        print("[DEBUG MODE] Subsampling 200 train and 50 val images...")
        train_df = train_df.iloc[: min(config.DEBUG_TRAIN_SAMPLES, len(train_df))].copy()
        val_df = val_df.iloc[: min(config.DEBUG_VAL_SAMPLES, len(val_df))].copy()
        total_epochs = config.DEBUG_EPOCHS if epochs is None else epochs
    else:
        total_epochs = config.MAX_EPOCHS if epochs is None else epochs

    cur_batch_size = config.BATCH_SIZE if batch_size is None else batch_size

    # DataLoaders
    train_dataset = CrackSegDataset(train_df, data_root=data_root, is_train=True)
    val_dataset = CrackSegDataset(val_df, data_root=data_root, is_train=False)

    train_loader = DataLoader(
        train_dataset,
        batch_size=cur_batch_size,
        shuffle=True,
        num_workers=config.WORKERS,
        pin_memory=torch.cuda.is_available(),
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=1,  # Evaluation uses batch_size=1 to accommodate mixed image dimensions in CRACK500 (e.g. 640x360 vs 648x484)
        shuffle=False,
        num_workers=config.WORKERS,
        pin_memory=torch.cuda.is_available(),
    )

    # Model
    model = build_model(
        model_name=model_name,
        encoder_name=config.ENCODER_BACKBONE,
        encoder_weights=config.ENCODER_WEIGHTS,
        in_channels=config.IN_CHANNELS,
        classes=config.NUM_CLASSES,
    ).to(device)

    # Optimizer: separate backbone (3e-4) and decoder (1e-3)
    encoder_params = list(model.encoder.parameters())
    decoder_params = [p for n, p in model.named_parameters() if not n.startswith("encoder")]

    optimizer = torch.optim.AdamW(
        [
            {"params": encoder_params, "lr": config.LR_ENCODER},
            {"params": decoder_params, "lr": config.LR_DECODER},
        ],
        weight_decay=config.WEIGHT_DECAY,
    )

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=total_epochs,
        eta_min=config.COSINE_ETA_MIN,
    )

    criterion = CombinedBCEDiceLoss(bce_weight=1.0, dice_weight=1.0)
    device_type = "cuda" if device.type == "cuda" else "cpu"
    use_amp = config.MIXED_PRECISION and (device.type == "cuda")

    if hasattr(torch, "amp") and hasattr(torch.amp, "GradScaler"):
        scaler = torch.amp.GradScaler(device_type, enabled=use_amp)
    else:
        scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    def autocast_ctx():
        if hasattr(torch, "amp") and hasattr(torch.amp, "autocast"):
            return torch.amp.autocast(device_type, enabled=use_amp)
        return torch.cuda.amp.autocast(enabled=use_amp)

    start_epoch = 1
    best_val_dice = -1.0
    patience_counter = 0
    history: List[Dict[str, Any]] = []

    # Resume from last.pth if exists
    if last_pth.exists():
        print(f"[RESUME] Loading checkpoint from: {last_pth}")
        checkpoint = torch.load(last_pth, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        if "scaler_state_dict" in checkpoint and scaler.is_enabled():
            scaler.load_state_dict(checkpoint["scaler_state_dict"])
        start_epoch = checkpoint["epoch"] + 1
        best_val_dice = checkpoint.get("best_val_dice", -1.0)
        patience_counter = checkpoint.get("patience_counter", 0)
        if history_csv.exists():
            history = pd.read_csv(history_csv).to_dict("records")
        print(f"[RESUME] Resuming at epoch {start_epoch}, previous best val Dice: {best_val_dice:.4f}")

    print("=" * 70)
    print(f"Starting Segmentation Training: {model_name} ({run_name})")
    print(f"  Encoder Backbone     : {config.ENCODER_BACKBONE} (ImageNet weights)")
    print(f"  Training Samples     : {len(train_dataset):,}")
    print(f"  Validation Samples   : {len(val_dataset):,}")
    print(f"  Batch Size           : {cur_batch_size}")
    print(f"  Max Epochs           : {total_epochs}")
    print(f"  Early Stop Patience  : {config.EARLY_STOPPING_PATIENCE}")
    print(f"  Learning Rates       : Encoder {config.LR_ENCODER}, Decoder {config.LR_DECODER}")
    print(f"  Mixed Precision      : {config.MIXED_PRECISION}")
    print("=" * 70)

    for epoch in range(start_epoch, total_epochs + 1):
        t0 = time.time()
        model.train()
        train_loss_accum = 0.0
        train_dice_accum = 0.0
        train_steps = 0

        for imgs, masks, _, _, _ in train_loader:
            imgs = imgs.to(device)
            masks = masks.to(device)

            optimizer.zero_grad()
            with autocast_ctx():
                logits = model(imgs)
                loss = criterion(logits, masks)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss_accum += loss.item()
            with torch.no_grad():
                probs = torch.sigmoid(logits)
                d_val, _ = compute_batch_dice_iou(probs, masks, threshold=0.5)
                train_dice_accum += d_val
            train_steps += 1

        scheduler.step()

        avg_train_loss = train_loss_accum / max(1, train_steps)
        avg_train_dice = train_dice_accum / max(1, train_steps)

        # Validation Phase
        model.eval()
        val_loss_accum = 0.0
        val_dice_accum = 0.0
        val_iou_accum = 0.0
        val_steps = 0

        with torch.no_grad():
            for imgs, masks, orig_hs, orig_ws, _ in val_loader:
                imgs = imgs.to(device)
                masks = masks.to(device)

                with autocast_ctx():
                    logits = model(imgs)
                    v_loss = criterion(logits, masks)

                val_loss_accum += v_loss.item()
                probs = torch.sigmoid(logits)

                # Compute metrics on unpadded regions
                for i in range(len(orig_hs)):
                    oh, ow = int(orig_hs[i]), int(orig_ws[i])
                    p_crop = probs[i : i + 1, :, :oh, :ow].contiguous()
                    m_crop = masks[i : i + 1, :, :oh, :ow].contiguous()
                    d_score, i_score = compute_batch_dice_iou(p_crop, m_crop, threshold=0.5)
                    val_dice_accum += d_score
                    val_iou_accum += i_score
                    val_steps += 1

        avg_val_loss = val_loss_accum / max(1, len(val_loader))
        avg_val_dice = val_dice_accum / max(1, val_steps)
        avg_val_iou = val_iou_accum / max(1, val_steps)
        epoch_time = time.time() - t0

        cur_lr_enc = optimizer.param_groups[0]["lr"]
        cur_lr_dec = optimizer.param_groups[1]["lr"]

        history.append({
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 4),
            "train_dice": round(avg_train_dice, 4),
            "val_loss": round(avg_val_loss, 4),
            "val_dice": round(avg_val_dice, 4),
            "val_iou": round(avg_val_iou, 4),
            "lr_encoder": cur_lr_enc,
            "lr_decoder": cur_lr_dec,
            "time_sec": round(epoch_time, 2),
        })
        pd.DataFrame(history).to_csv(history_csv, index=False)

        print(
            f"Epoch [{epoch:2d}/{total_epochs:2d}] "
            f"Train Loss: {avg_train_loss:.4f} | Train Dice: {avg_train_dice:.4f} | "
            f"Val Loss: {avg_val_loss:.4f} | Val Dice: {avg_val_dice:.4f} | Val IoU: {avg_val_iou:.4f} | "
            f"Time: {epoch_time:.1f}s"
        )

        # Save last checkpoint
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "scaler_state_dict": scaler.state_dict() if scaler.is_enabled() else {},
                "best_val_dice": best_val_dice,
                "patience_counter": patience_counter,
            },
            last_pth,
        )

        # Check for improvement on Validation Dice
        if avg_val_dice > best_val_dice:
            best_val_dice = avg_val_dice
            patience_counter = 0
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "val_dice": best_val_dice,
                    "val_iou": avg_val_iou,
                },
                best_pth,
            )
            print(f"  -> [SAVED BEST] New best validation Dice: {best_val_dice:.4f}")
        else:
            patience_counter += 1
            if patience_counter >= config.EARLY_STOPPING_PATIENCE and not debug:
                print(f"[EARLY STOPPING] Validation Dice did not improve for {config.EARLY_STOPPING_PATIENCE} epochs.")
                break

    # Load best weights before threshold sweep
    if best_pth.exists():
        best_ckpt = torch.load(best_pth, map_location=device)
        model.load_state_dict(best_ckpt["model_state_dict"])
        print(f"[BEST MODEL LOADED] Successfully loaded weights from epoch {best_ckpt.get('epoch')}")

    # Threshold sweep on validation split
    optimal_threshold, sweep_df = sweep_validation_thresholds(
        model=model,
        val_loader=val_loader,
        device=device,
    )
    sweep_df.to_csv(sweep_csv_path, index=False)
    print(f"[OK] Saved validation threshold sweep to: {sweep_csv_path}")

    # Run Card
    try:
        import segmentation_models_pytorch as smp
        smp_ver = getattr(smp, "__version__", "unknown")
    except Exception:
        smp_ver = "unknown"

    hw_info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cuda_available": torch.cuda.is_available(),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
    }

    run_card = {
        "model_name": model_name,
        "run_name": run_name,
        "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "torch_version": torch.__version__,
        "smp_version": smp_ver,
        "seed": seed,
        "debug_mode": debug,
        "hyperparameters": {
            "encoder": config.ENCODER_BACKBONE,
            "encoder_weights": config.ENCODER_WEIGHTS,
            "image_crop_train": config.IMAGE_SIZE_TRAIN,
            "pad_multiple_eval": config.PAD_MULTIPLE_EVAL,
            "batch_size": cur_batch_size,
            "max_epochs": total_epochs,
            "early_stopping_patience": config.EARLY_STOPPING_PATIENCE,
            "lr_encoder": config.LR_ENCODER,
            "lr_decoder": config.LR_DECODER,
            "mixed_precision": config.MIXED_PRECISION,
        },
        "dataset_counts": {
            "train": len(train_df),
            "val": len(val_df),
        },
        "best_validation_results": {
            "best_val_dice_at_05": round(best_val_dice, 4),
            "optimal_threshold": round(optimal_threshold, 2),
            "optimal_val_dice": round(float(sweep_df.loc[sweep_df['threshold'] == optimal_threshold, 'val_dice'].values[0]), 4) if len(sweep_df) else round(best_val_dice, 4),
        },
        "hardware": hw_info,
    }

    with open(run_card_path, "w", encoding="utf-8") as f:
        json.dump(run_card, f, indent=2)
    print(f"[OK] Run card saved at: {run_card_path}")

    return {
        "run_dir": str(run_dir),
        "best_pth": str(best_pth),
        "best_val_dice": best_val_dice,
        "optimal_threshold": optimal_threshold,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="InfraScan Crack Segmentation Training")
    parser.add_argument("--model", type=str, default="unet", choices=["unet", "unetplusplus"])
    parser.add_argument("--manifest", type=str, required=True, help="Path to crack500 manifest CSV")
    parser.add_argument("--project", type=str, default="/kaggle/working/models/segmentation")
    parser.add_argument("--name", type=str, default="unet_crack500")
    parser.add_argument("--data_root", type=str, default="")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch", type=int, default=None)
    parser.add_argument("--device", type=str, default="cuda:0")

    args = parser.parse_args()

    train(
        model_name=args.model,
        manifest_csv=args.manifest,
        project_dir=args.project,
        run_name=args.name,
        data_root=args.data_root,
        debug=args.debug,
        epochs=args.epochs,
        batch_size=args.batch,
        device_str=args.device,
    )

