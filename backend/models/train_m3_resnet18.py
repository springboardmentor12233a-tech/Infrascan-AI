
from pathlib import Path
import json
import random

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)

# Paths
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "dataset" / "split_data"
OUTPUT_DIR = BASE_DIR / "backend" / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = OUTPUT_DIR / "m3_resnet18.pth"
METRICS_PATH = OUTPUT_DIR / "m3_resnet18_metrics.json"

# Settings
SEED = 42
IMAGE_SIZE = 224
BATCH_SIZE = 16
EPOCHS = 10
LEARNING_RATE = 0.0001
DEVICE = torch.device("cpu")

random.seed(SEED)
torch.manual_seed(SEED)

# ImageNet normalization
train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225],
    ),
])

eval_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225],
    ),
])

# Datasets
train_dataset = datasets.ImageFolder(
    DATA_DIR / "train", transform=train_transform
)
val_dataset = datasets.ImageFolder(
    DATA_DIR / "val", transform=eval_transform
)
test_dataset = datasets.ImageFolder(
    DATA_DIR / "test", transform=eval_transform
)

classes = train_dataset.classes

if not (
    classes == val_dataset.classes == test_dataset.classes
):
    raise ValueError("Class folders do not match across splits.")

train_loader = DataLoader(
    train_dataset, batch_size=BATCH_SIZE,
    shuffle=True, num_workers=0
)
val_loader = DataLoader(
    val_dataset, batch_size=BATCH_SIZE,
    shuffle=False, num_workers=0
)
test_loader = DataLoader(
    test_dataset, batch_size=BATCH_SIZE,
    shuffle=False, num_workers=0
)

print("Classes:", classes)
print("Train:", len(train_dataset))
print("Validation:", len(val_dataset))
print("Test:", len(test_dataset))
print("Device:", DEVICE)

# Load pretrained ResNet18
weights = models.ResNet18_Weights.DEFAULT
model = models.resnet18(weights=weights)

# Freeze early feature layers initially
for param in model.parameters():
    param.requires_grad = False

# Replace final layer for six classes
model.fc = nn.Linear(model.fc.in_features, len(classes))
model = model.to(DEVICE)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(
    model.fc.parameters(), lr=LEARNING_RATE
)

best_val_f1 = -1.0

# Training
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0.0

    for images, labels in train_loader:
        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    # Validation
    model.eval()
    val_true, val_pred = [], []

    with torch.no_grad():
        for images, labels in val_loader:
            outputs = model(images.to(DEVICE))
            predictions = outputs.argmax(dim=1)

            val_true.extend(labels.tolist())
            val_pred.extend(predictions.cpu().tolist())

    val_acc = accuracy_score(val_true, val_pred)
    val_f1 = f1_score(
        val_true, val_pred,
        average="macro", zero_division=0
    )

    print(
        f"Epoch {epoch + 1}/{EPOCHS} | "
        f"Loss: {total_loss / len(train_loader):.4f} | "
        f"Val Accuracy: {val_acc:.4f} | "
        f"Val Macro F1: {val_f1:.4f}"
    )

    if val_f1 > best_val_f1:
        best_val_f1 = val_f1

        torch.save({
            "model_state_dict": model.state_dict(),
            "classes": classes,
            "image_size": IMAGE_SIZE,
            "best_validation_f1": best_val_f1,
            "seed": SEED,
        }, MODEL_PATH)

        print("Best ResNet18 checkpoint saved.")

# Load best checkpoint
checkpoint = torch.load(
    MODEL_PATH, map_location=DEVICE, weights_only=True
)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

# Final held-out test evaluation
test_true, test_pred = [], []

with torch.no_grad():
    for images, labels in test_loader:
        outputs = model(images.to(DEVICE))
        predictions = outputs.argmax(dim=1)

        test_true.extend(labels.tolist())
        test_pred.extend(predictions.cpu().tolist())

metrics = {
    "model": "ResNet18 transfer learning",
    "classes": classes,
    "test_images": len(test_dataset),
    "test_accuracy": float(
        accuracy_score(test_true, test_pred)
    ),
    "test_precision_macro": float(
        precision_score(
            test_true, test_pred,
            average="macro", zero_division=0
        )
    ),
    "test_recall_macro": float(
        recall_score(
            test_true, test_pred,
            average="macro", zero_division=0
        )
    ),
    "test_f1_macro": float(
        f1_score(
            test_true, test_pred,
            average="macro", zero_division=0
        )
    ),
    "confusion_matrix": confusion_matrix(
        test_true, test_pred,
        labels=list(range(len(classes)))
    ).tolist(),
}

with open(METRICS_PATH, "w", encoding="utf-8") as file:
    json.dump(metrics, file, indent=2)

print("\nFINAL RESNET18 TEST RESULTS")
print(json.dumps(metrics, indent=2))

print("\nClassification report:")
print(classification_report(
    test_true,
    test_pred,
    labels=list(range(len(classes))),
    target_names=classes,
    zero_division=0,
))

print("Model saved:", MODEL_PATH)
print("Metrics saved:", METRICS_PATH)
