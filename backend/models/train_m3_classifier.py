from pathlib import Path
import json
import random

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

# Paths
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "dataset" / "split_data"
OUTPUT_DIR = BASE_DIR / "backend" / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = OUTPUT_DIR / "m3_six_class_cnn.pth"
METRICS_PATH = OUTPUT_DIR / "m3_six_class_metrics.json"

# Reproducibility and CPU-friendly settings
SEED = 42
random.seed(SEED)
torch.manual_seed(SEED)

DEVICE = torch.device("cpu")
IMAGE_SIZE = 128
BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 0.001

train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
])

eval_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
])

# Load existing train / validation / test folders
train_dataset = datasets.ImageFolder(DATA_DIR / "train", transform=train_transform)
val_dataset = datasets.ImageFolder(DATA_DIR / "val", transform=eval_transform)
test_dataset = datasets.ImageFolder(DATA_DIR / "test", transform=eval_transform)

if train_dataset.classes != val_dataset.classes or train_dataset.classes != test_dataset.classes:
    raise ValueError("Train, validation, and test class folders do not match.")

classes = train_dataset.classes

train_loader = DataLoader(
    train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0
)
val_loader = DataLoader(
    val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0
)
test_loader = DataLoader(
    test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0
)

class SixClassCNN(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


model = SixClassCNN(len(classes)).to(DEVICE)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

best_val_f1 = -1.0

print("Classes:", classes)
print(f"Images — train: {len(train_dataset)}, val: {len(val_dataset)}, test: {len(test_dataset)}")
print("Device:", DEVICE)

# Train; choose checkpoint using validation macro-F1
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0.0

    for images, labels in train_loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    model.eval()
    val_true, val_pred = [], []

    with torch.no_grad():
        for images, labels in val_loader:
            outputs = model(images.to(DEVICE))
            val_pred.extend(outputs.argmax(dim=1).cpu().tolist())
            val_true.extend(labels.tolist())

    val_accuracy = accuracy_score(val_true, val_pred)
    val_f1 = f1_score(val_true, val_pred, average="macro", zero_division=0)

    print(
        f"Epoch {epoch + 1}/{EPOCHS} | "
        f"Loss: {total_loss / max(len(train_loader), 1):.4f} | "
        f"Val accuracy: {val_accuracy:.4f} | Val macro-F1: {val_f1:.4f}"
    )

    if val_f1 > best_val_f1:
        best_val_f1 = val_f1
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "classes": classes,
                "image_size": IMAGE_SIZE,
                "best_validation_f1": best_val_f1,
                "seed": SEED,
            },
            MODEL_PATH,
        )
        print("Saved best checkpoint.")

# Evaluate the selected checkpoint on the held-out test split
checkpoint = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

test_true, test_pred = [], []
with torch.no_grad():
    for images, labels in test_loader:
        outputs = model(images.to(DEVICE))
        test_pred.extend(outputs.argmax(dim=1).cpu().tolist())
        test_true.extend(labels.tolist())

metrics = {
    "model": "SixClassCNN",
    "classes": classes,
    "test_images": len(test_dataset),
    "test_accuracy": float(accuracy_score(test_true, test_pred)),
    "test_macro_f1": float(
        f1_score(test_true, test_pred, average="macro", zero_division=0)
    ),
    "confusion_matrix": confusion_matrix(
        test_true, test_pred, labels=list(range(len(classes)))
    ).tolist(),
    "classification_report": classification_report(
        test_true,
        test_pred,
        labels=list(range(len(classes))),
        target_names=classes,
        output_dict=True,
        zero_division=0,
    ),
}

METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

print("\nTest accuracy:", f"{metrics['test_accuracy']:.4f}")
print("Test macro-F1:", f"{metrics['test_macro_f1']:.4f}")
print("\nClassification report:")
print(classification_report(
    test_true,
    test_pred,
    labels=list(range(len(classes))),
    target_names=classes,
    zero_division=0,
))
print(f"Model saved: {MODEL_PATH}")
print(f"Metrics saved: {METRICS_PATH}")