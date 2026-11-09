"""
InfraScan ML Model Training Pipeline – Dual-Dataset Enhanced Training
Trains concrete crack detection model using both:
1. SDNET2018 Multi-Infrastructure Benchmark (Decks, Pavements, Walls)
2. METU Concrete Crack Images Benchmark (Secondary Dataset)

Exports high-accuracy model to PyTorch (.pt) and optimized ONNX (.onnx) for production inference.
"""

import os
import glob
import random
import time
from typing import List, Tuple
from PIL import Image
import numpy as np

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import onnx
import onnxruntime as ort

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_ROOT = os.path.join(BASE_DIR, "dataset")
METU_DATASET_ROOT = os.path.join(BASE_DIR, "second_dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")

BATCH_SIZE = 32
EPOCHS = 6
LEARNING_RATE = 5e-4
RANDOM_SEED = 42

random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


def find_sdnet_images(root_dir: str) -> Tuple[List[str], List[str]]:
    valid_exts = ("*.jpg", "*.jpeg", "*.png")
    cracked = []
    uncracked = []
    for ext in valid_exts:
        cracked.extend(glob.glob(os.path.join(root_dir, "*", "Cracked", ext)))
        uncracked.extend(glob.glob(os.path.join(root_dir, "*", "Non-cracked", ext)))
    if not cracked or not uncracked:
        for ext in valid_exts:
            cracked.extend(glob.glob(os.path.join(root_dir, "**", "Cracked", ext), recursive=True))
            uncracked.extend(glob.glob(os.path.join(root_dir, "**", "Non-cracked", ext), recursive=True))
    return cracked, uncracked


def find_metu_dataset_images(root_dir: str) -> Tuple[List[str], List[str]]:
    valid_exts = ("*.jpg", "*.jpeg", "*.png")
    cracked = []
    uncracked = []
    for ext in valid_exts:
        cracked.extend(glob.glob(os.path.join(root_dir, "*", "Positive", ext)))
        uncracked.extend(glob.glob(os.path.join(root_dir, "*", "Negative", ext)))
    return cracked, uncracked


class ConcreteCrackDataset(Dataset):
    def __init__(self, file_paths: List[str], labels: List[int], transform=None):
        self.file_paths = file_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        path = self.file_paths[idx]
        label = self.labels[idx]
        with Image.open(path) as img:
            img = img.convert("RGB")
            if self.transform:
                img = self.transform(img)
        return img, torch.tensor(label, dtype=torch.float32)


def get_transforms():
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    return train_transform, val_transform


def build_model():
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 128),
        nn.Hardswish(),
        nn.Dropout(p=0.3),
        nn.Linear(128, 1)
    )
    return model


def train():
    os.makedirs(MODELS_DIR, exist_ok=True)
    print("=" * 65)
    print("   INFRASCAN AI: DUAL-DATASET CONCRETE CRACK TRAINING PIPELINE   ")
    print("=" * 65)

    # 1. Primary Dataset: SDNET2018
    print(f"\n1. Scanning Primary Dataset (SDNET2018) in: {DATASET_ROOT}")
    sdnet_c, sdnet_u = find_sdnet_images(DATASET_ROOT)
    print(f"   Found {len(sdnet_c)} cracked and {len(sdnet_u)} uncracked SDNET images.")

    # 2. Secondary Dataset: METU Concrete Crack Images
    print(f"\n2. Scanning Secondary Dataset (METU Benchmark) in: {METU_DATASET_ROOT}")
    second_c, second_u = find_metu_dataset_images(METU_DATASET_ROOT)
    print(f"   Found {len(second_c)} cracked (Positive) and {len(second_u)} uncracked (Negative) images.")

    # Sample balanced pools from both
    # 2,000 from SDNET (1,000 cracked, 1,000 uncracked)
    # 4,000 from METU (2,000 cracked, 2,000 uncracked)
    # Total = 6,000 images (3,000 cracked, 3,000 uncracked)
    n_sdnet_c = min(len(sdnet_c), 1500)
    n_sdnet_u = min(len(sdnet_u), 1500)
    n_second_c = min(len(second_c), 2500)
    n_second_u = min(len(second_u), 2500)

    sampled_sdnet_c = random.sample(sdnet_c, n_sdnet_c)
    sampled_sdnet_u = random.sample(sdnet_u, n_sdnet_u)
    sampled_second_c = random.sample(second_c, n_second_c)
    sampled_second_u = random.sample(second_u, n_second_u)

    total_cracked = sampled_sdnet_c + sampled_second_c
    total_uncracked = sampled_sdnet_u + sampled_second_u

    print(f"\nDual Dataset Training Composition:")
    print(f"   • SDNET2018: {n_sdnet_c} cracked + {n_sdnet_u} uncracked = {n_sdnet_c + n_sdnet_u}")
    print(f"   • METU 2nd Dataset: {n_second_c} cracked + {n_second_u} uncracked = {n_second_c + n_second_u}")
    print(f"   • Total Balanced Pool: {len(total_cracked)} cracked + {len(total_uncracked)} uncracked = {len(total_cracked) + len(total_uncracked)} images")

    all_files = total_cracked + total_uncracked
    all_labels = [1] * len(total_cracked) + [0] * len(total_uncracked)

    # 70% train, 15% val, 15% test
    train_files, test_files, train_y, test_y = train_test_split(
        all_files, all_labels, test_size=0.30, random_state=RANDOM_SEED, stratify=all_labels
    )
    val_files, test_files, val_y, test_y = train_test_split(
        test_files, test_y, test_size=0.50, random_state=RANDOM_SEED, stratify=test_y
    )

    print(f"Dataset Splits: Train={len(train_files)}, Val={len(val_files)}, Test={len(test_files)}")

    train_tf, val_tf = get_transforms()

    train_loader = DataLoader(ConcreteCrackDataset(train_files, train_y, train_tf), batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(ConcreteCrackDataset(val_files, val_y, val_tf), batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(ConcreteCrackDataset(test_files, test_y, val_tf), batch_size=BATCH_SIZE, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device}")

    model = build_model().to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_val_loss = float("inf")
    best_weights_path = os.path.join(MODELS_DIR, "crack_classifier.pt")

    for epoch in range(1, EPOCHS + 1):
        start_time = time.time()
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for imgs, labels in train_loader:
            imgs = imgs.to(device)
            labels = labels.to(device).unsqueeze(1)

            optimizer.zero_grad()
            logits = model(imgs)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * len(labels)
            preds = (torch.sigmoid(logits) > 0.5).float()
            train_correct += (preds == labels).sum().item()
            train_total += len(labels)

        scheduler.step()
        epoch_train_loss = train_loss / train_total
        epoch_train_acc = train_correct / train_total

        # Validation
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs = imgs.to(device)
                labels = labels.to(device).unsqueeze(1)

                logits = model(imgs)
                loss = criterion(logits, labels)

                val_loss += loss.item() * len(labels)
                preds = (torch.sigmoid(logits) > 0.5).float()
                val_correct += (preds == labels).sum().item()
                val_total += len(labels)

        epoch_val_loss = val_loss / val_total
        epoch_val_acc = val_correct / val_total
        elapsed = time.time() - start_time

        print(
            f"Epoch [{epoch}/{EPOCHS}] ({elapsed:.1f}s) - "
            f"Train Loss: {epoch_train_loss:.4f}, Train Acc: {epoch_train_acc*100:.2f}% | "
            f"Val Loss: {epoch_val_loss:.4f}, Val Acc: {epoch_val_acc*100:.2f}%"
        )

        if epoch_val_loss < best_val_loss:
            best_val_loss = epoch_val_loss
            torch.save(model.state_dict(), best_weights_path)
            print(f"  --> Saved new best model checkpoint (Val Acc: {epoch_val_acc*100:.2f}%)")

    # Evaluation on Held-Out Test Set
    print("\n" + "=" * 50)
    print("Evaluating on Held-Out Combined Test Set...")
    model.load_state_dict(torch.load(best_weights_path))
    model.eval()

    test_preds = []
    test_targets = []

    with torch.no_grad():
        for imgs, labels in test_loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs = torch.sigmoid(logits).cpu().numpy().flatten()
            test_preds.extend((probs > 0.5).astype(int))
            test_targets.extend(labels.numpy().astype(int))

    print("\nClassification Report (Held-Out Test Set):")
    print(classification_report(test_targets, test_preds, target_names=["Uncracked", "Cracked"], digits=4))
    print("Confusion Matrix:")
    print(confusion_matrix(test_targets, test_preds))

    # Export to ONNX
    print("\n" + "=" * 50)
    print("Exporting model to ONNX for fast inference...")
    model.cpu()
    dummy_input = torch.randn(1, 3, 224, 224, dtype=torch.float32)
    onnx_path = os.path.join(MODELS_DIR, "crack_classifier.onnx")

    class InferenceModel(nn.Module):
        def __init__(self, base_model):
            super().__init__()
            self.base_model = base_model

        def forward(self, x):
            logits = self.base_model(x)
            return torch.sigmoid(logits)

    export_model = InferenceModel(model)
    export_model.eval()

    torch.onnx.export(
        export_model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["confidence"],
        dynamic_axes={"input": {0: "batch_size"}, "confidence": {0: "batch_size"}}
    )
    print(f"ONNX model saved successfully to: {onnx_path}")

    # Validate ONNX model with onnxruntime
    print("Verifying ONNX model with ONNX Runtime...")
    ort_session = ort.InferenceSession(onnx_path)
    sample_np = np.random.randn(1, 3, 224, 224).astype(np.float32)
    ort_outs = ort_session.run(None, {"input": sample_np})
    print(f"ONNX inference test passed! Sample output: {ort_outs[0]}")
    print("\nTraining and Export Complete!")


if __name__ == "__main__":
    train()
