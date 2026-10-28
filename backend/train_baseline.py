
from pathlib import Path
import cv2
import numpy as np
import joblib
import json
from sklearn.svm import LinearSVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report
)

# Project paths
BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "dataset" / "split_data"
OUT = BASE / "backend" / "models"
OUT.mkdir(parents=True, exist_ok=True)

PARTS = ("train", "val", "test")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}

# HOG feature extractor (no PyTorch required)
hog = cv2.HOGDescriptor(
    (128, 128), (16, 16), (8, 8), (8, 8), 9
)

def load_features(part):
    folder = DATA / part
    if not folder.exists():
        raise FileNotFoundError(f"Missing folder: {folder}")

    features, labels = [], []
    for class_dir in sorted(p for p in folder.iterdir() if p.is_dir()):
        files = sorted(
            p for p in class_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        )
        print(f"{part}: reading {class_dir.name} ({len(files)} images)")
        for i, path in enumerate(files, 1):
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                print(f"WARNING: unreadable image: {path.name}")
                continue
            image = cv2.resize(image, (128, 128))
            feature = hog.compute(image).reshape(-1)
            features.append(feature)
            labels.append(class_dir.name)

            if i % 500 == 0:
                print(f"  processed {i}/{len(files)}")

    if not features:
        raise RuntimeError(f"No images loaded from {folder}")

    return np.asarray(features, dtype=np.float32), np.asarray(labels)

print("Loading training images...")
X_train, y_train = load_features("train")
print("Loading validation images...")
X_val, y_val = load_features("val")

print("\nTraining HOG + Linear SVM baseline...")
model = LinearSVC(C=1.0, max_iter=5000, random_state=42)
model.fit(X_train, y_train)

val_pred = model.predict(X_val)
print("\nValidation accuracy:", round(accuracy_score(y_val, val_pred), 4))
print(classification_report(y_val, val_pred, zero_division=0))

print("Loading held-out test images...")
X_test, y_test = load_features("test")
test_pred = model.predict(X_test)

metrics = {
    "model": "HOG + LinearSVC baseline",
    "test_accuracy": float(accuracy_score(y_test, test_pred)),
    "test_precision_macro": float(
        precision_score(y_test, test_pred, average="macro", zero_division=0)
    ),
    "test_recall_macro": float(
        recall_score(y_test, test_pred, average="macro", zero_division=0)
    ),
    "test_f1_macro": float(
        f1_score(y_test, test_pred, average="macro", zero_division=0)
    ),
    "classes": sorted(np.unique(y_test).tolist()),
    "confusion_matrix": confusion_matrix(
        y_test, test_pred, labels=sorted(np.unique(y_test))
    ).tolist()
}

print("\n===== FINAL HELD-OUT TEST METRICS =====")
print(json.dumps(metrics, indent=2))
print("\nPer-class report:")
print(classification_report(y_test, test_pred, zero_division=0))

joblib.dump(model, OUT / "crack_baseline_svm.joblib")
with open(OUT / "baseline_metrics.json", "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2)

print(f"\nModel saved: {OUT / 'crack_baseline_svm.joblib'}")
print(f"Metrics saved: {OUT / 'baseline_metrics.json'}")
print("BASELINE TRAINING AND TESTING COMPLETE")
