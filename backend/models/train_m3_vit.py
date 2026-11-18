
import json
import csv
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms


# =====================================================
# CONFIGURATION
# =====================================================

SEED = 42
IMAGE_SIZE = 64
PATCH_SIZE = 8
BATCH_SIZE = 32
EPOCHS = 15
LEARNING_RATE = 0.0003
WEIGHT_DECAY = 0.0001

DEVICE = torch.device("cpu")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "dataset" / "split_data"
OUTPUT_DIR = Path(__file__).resolve().parent

MODEL_PATH = OUTPUT_DIR / "m3_vit_small.pth"
METRICS_PATH = OUTPUT_DIR / "m3_vit_metrics.json"
REPORT_PATH = OUTPUT_DIR / "m3_vit_classification_report.txt"
CONFUSION_PATH = OUTPUT_DIR / "m3_vit_confusion_matrix.csv"


# =====================================================
# METRICS WITHOUT SCIKIT-LEARN
# =====================================================

def calculate_metrics(y_true, y_pred, num_classes, class_names):

    matrix = np.zeros(
        (num_classes, num_classes),
        dtype=int
    )

    for actual, predicted in zip(y_true, y_pred):
        matrix[actual][predicted] += 1

    precision_values = []
    recall_values = []
    f1_values = []

    report_lines = []

    report_lines.append(
        f"{'Class':<12} {'Precision':>12} "
        f"{'Recall':>12} {'F1-score':>12} {'Support':>10}"
    )

    report_lines.append("-" * 62)

    for i in range(num_classes):

        tp = matrix[i, i]
        fp = matrix[:, i].sum() - tp
        fn = matrix[i, :].sum() - tp

        precision = (
            tp / (tp + fp)
            if tp + fp > 0 else 0.0
        )

        recall = (
            tp / (tp + fn)
            if tp + fn > 0 else 0.0
        )

        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall > 0 else 0.0
        )

        support = int(matrix[i, :].sum())

        precision_values.append(precision)
        recall_values.append(recall)
        f1_values.append(f1)

        report_lines.append(
            f"{class_names[i]:<12} "
            f"{precision:>12.4f} "
            f"{recall:>12.4f} "
            f"{f1:>12.4f} "
            f"{support:>10}"
        )

    accuracy = (
        np.trace(matrix) / matrix.sum()
        if matrix.sum() > 0 else 0.0
    )

    macro_precision = float(np.mean(precision_values))
    macro_recall = float(np.mean(recall_values))
    macro_f1 = float(np.mean(f1_values))

    report = "\n".join(report_lines)

    return (
        float(accuracy),
        macro_precision,
        macro_recall,
        macro_f1,
        report,
        matrix
    )


# =====================================================
# REPRODUCIBILITY
# =====================================================

def set_seed(seed):

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


# =====================================================
# PATCH EMBEDDING
# =====================================================

class PatchEmbedding(nn.Module):

    def __init__(self, image_size, patch_size, embed_dim):

        super().__init__()

        self.projection = nn.Conv2d(
            3,
            embed_dim,
            kernel_size=patch_size,
            stride=patch_size
        )

        num_patches = (
            image_size // patch_size
        ) ** 2

        self.class_token = nn.Parameter(
            torch.zeros(1, 1, embed_dim)
        )

        self.position_embedding = nn.Parameter(
            torch.zeros(1, num_patches + 1, embed_dim)
        )

    def forward(self, images):

        patches = self.projection(images)

        patches = patches.flatten(2).transpose(1, 2)

        class_tokens = self.class_token.expand(
            images.shape[0], -1, -1
        )

        tokens = torch.cat(
            (class_tokens, patches),
            dim=1
        )

        return tokens + self.position_embedding


# =====================================================
# TRANSFORMER BLOCK
# =====================================================

class TransformerBlock(nn.Module):

    def __init__(self, embed_dim, num_heads, mlp_ratio=2):

        super().__init__()

        self.norm1 = nn.LayerNorm(embed_dim)

        self.attention = nn.MultiheadAttention(
            embed_dim,
            num_heads,
            batch_first=True
        )

        self.norm2 = nn.LayerNorm(embed_dim)

        self.mlp = nn.Sequential(
            nn.Linear(
                embed_dim,
                embed_dim * mlp_ratio
            ),
            nn.GELU(),
            nn.Linear(
                embed_dim * mlp_ratio,
                embed_dim
            )
        )

    def forward(self, x):

        normalized = self.norm1(x)

        attended, _ = self.attention(
            normalized,
            normalized,
            normalized,
            need_weights=False
        )

        x = x + attended

        x = x + self.mlp(self.norm2(x))

        return x


# =====================================================
# VISION TRANSFORMER MODEL
# =====================================================

class SmallVisionTransformer(nn.Module):

    def __init__(self, num_classes):

        super().__init__()

        self.patch_embedding = PatchEmbedding(
            IMAGE_SIZE,
            PATCH_SIZE,
            embed_dim=128
        )

        self.blocks = nn.Sequential(
            *[
                TransformerBlock(
                    128,
                    num_heads=4
                )
                for _ in range(4)
            ]
        )

        self.norm = nn.LayerNorm(128)

        self.head = nn.Linear(
            128,
            num_classes
        )

    def forward(self, images):

        x = self.patch_embedding(images)

        x = self.blocks(x)

        x = self.norm(x[:, 0])

        return self.head(x)


# =====================================================
# TRAINING AND VALIDATION
# =====================================================

def run_epoch(
    model,
    loader,
    criterion,
    optimizer=None
):

    training = optimizer is not None

    model.train(training)

    total_loss = 0.0

    all_labels = []
    all_predictions = []

    for images, labels in loader:

        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        if training:
            optimizer.zero_grad()

        with torch.set_grad_enabled(training):

            outputs = model(images)

            loss = criterion(outputs, labels)

            if training:

                loss.backward()
                optimizer.step()

        total_loss += loss.item() * images.size(0)

        predictions = outputs.argmax(dim=1)

        all_labels.extend(labels.cpu().tolist())

        all_predictions.extend(
            predictions.cpu().tolist()
        )

    average_loss = (
        total_loss / len(loader.dataset)
    )

    accuracy = sum(
        a == p
        for a, p in zip(all_labels, all_predictions)
    ) / len(all_labels)

    return average_loss, accuracy


# =====================================================
# MAIN FUNCTION
# =====================================================

def main():

    set_seed(SEED)

    if not DATA_DIR.exists():

        raise FileNotFoundError(
            f"Dataset not found: {DATA_DIR}"
        )

    # Training transformations

    train_transform = transforms.Compose([

        transforms.Resize(
            (IMAGE_SIZE, IMAGE_SIZE)
        ),

        transforms.RandomHorizontalFlip(),

        transforms.RandomVerticalFlip(),

        transforms.RandomRotation(10),

        transforms.ToTensor(),

        transforms.Normalize(
            (0.485, 0.456, 0.406),
            (0.229, 0.224, 0.225)
        )
    ])

    # Validation and testing transformations

    eval_transform = transforms.Compose([

        transforms.Resize(
            (IMAGE_SIZE, IMAGE_SIZE)
        ),

        transforms.ToTensor(),

        transforms.Normalize(
            (0.485, 0.456, 0.406),
            (0.229, 0.224, 0.225)
        )
    ])

    # Load datasets

    train_dataset = datasets.ImageFolder(
        DATA_DIR / "train",
        transform=train_transform
    )

    val_dataset = datasets.ImageFolder(
        DATA_DIR / "val",
        transform=eval_transform
    )

    test_dataset = datasets.ImageFolder(
        DATA_DIR / "test",
        transform=eval_transform
    )

    if (
        train_dataset.classes != val_dataset.classes
        or train_dataset.classes != test_dataset.classes
    ):

        raise ValueError(
            "Class folders differ between train, val and test."
        )

    classes = train_dataset.classes

    num_classes = len(classes)

    print("\nClasses:", classes)

    print("Training images:", len(train_dataset))
    print("Validation images:", len(val_dataset))
    print("Testing images:", len(test_dataset))

    print("Device:", DEVICE)

    # Data loaders

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0
    )

    # Initialize model

    model = SmallVisionTransformer(
        num_classes=num_classes
    ).to(DEVICE)

    criterion = nn.CrossEntropyLoss()

    best_val_accuracy = -1.0

    # =================================================
    # LOAD CHECKPOINT OR TRAIN
    # =================================================

    if MODEL_PATH.exists():

        print("\nExisting ViT checkpoint found.")

        print("Skipping training and loading saved model...")

        checkpoint = torch.load(
            MODEL_PATH,
            map_location=DEVICE,
            weights_only=False
        )

        if checkpoint.get("class_names") != classes:

            raise ValueError(
                "Checkpoint classes do not match dataset classes."
            )

        model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        model.eval()

        _, best_val_accuracy = run_epoch(
            model,
            val_loader,
            criterion
        )

        print(
            f"Validation accuracy: "
            f"{best_val_accuracy * 100:.2f}%"
        )

    else:

        print("\nStarting Vision Transformer training...\n")

        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=LEARNING_RATE,
            weight_decay=WEIGHT_DECAY
        )

        for epoch in range(EPOCHS):

            train_loss, train_acc = run_epoch(
                model,
                train_loader,
                criterion,
                optimizer
            )

            val_loss, val_acc = run_epoch(
                model,
                val_loader,
                criterion
            )

            print(
                f"Epoch {epoch + 1}/{EPOCHS} | "
                f"Train Loss: {train_loss:.4f} | "
                f"Train Accuracy: {train_acc * 100:.2f}% | "
                f"Val Loss: {val_loss:.4f} | "
                f"Val Accuracy: {val_acc * 100:.2f}%"
            )

            if val_acc > best_val_accuracy:

                best_val_accuracy = val_acc

                torch.save(
                    {
                        "model_state_dict": model.state_dict(),
                        "class_names": classes,
                        "image_size": IMAGE_SIZE,
                        "patch_size": PATCH_SIZE,
                        "architecture": "SmallVisionTransformer",
                        "pretrained": False
                    },
                    MODEL_PATH
                )

                print("Best model checkpoint saved.")

        # Load best saved model

        checkpoint = torch.load(
            MODEL_PATH,
            map_location=DEVICE,
            weights_only=False
        )

        model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        model.eval()

    # =================================================
    # FINAL TEST EVALUATION
    # =================================================

    print("\nRunning final test evaluation...")

    y_true = []
    y_pred = []

    with torch.no_grad():

        for images, labels in test_loader:

            outputs = model(
                images.to(DEVICE)
            )

            predictions = outputs.argmax(
                dim=1
            ).cpu()

            y_true.extend(
                labels.tolist()
            )

            y_pred.extend(
                predictions.tolist()
            )

    (
        accuracy,
        precision,
        recall,
        f1,
        report,
        matrix
    ) = calculate_metrics(
        y_true,
        y_pred,
        num_classes,
        classes
    )

    # =================================================
    # SAVE METRICS
    # =================================================

    metrics = {

        "model": "Lightweight Vision Transformer",

        "pretrained": False,

        "image_size": IMAGE_SIZE,

        "patch_size": PATCH_SIZE,

        "epochs": EPOCHS,

        "best_validation_accuracy": round(
            float(best_val_accuracy),
            6
        ),

        "test_accuracy": round(
            float(accuracy),
            6
        ),

        "test_precision_macro": round(
            float(precision),
            6
        ),

        "test_recall_macro": round(
            float(recall),
            6
        ),

        "test_f1_macro": round(
            float(f1),
            6
        ),

        "classes": classes,

        "test_images": len(test_dataset)
    }

    METRICS_PATH.write_text(
        json.dumps(metrics, indent=4),
        encoding="utf-8"
    )

    REPORT_PATH.write_text(
        report,
        encoding="utf-8"
    )

    # Save confusion matrix

    with CONFUSION_PATH.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            ["actual/predicted"] + classes
        )

        for class_name, row in zip(
            classes,
            matrix
        ):

            writer.writerow(
                [class_name] + row.tolist()
            )

    # =================================================
    # PRINT FINAL RESULTS
    # =================================================

    print("\n========== FINAL TEST RESULTS ==========")

    print(
        f"Test Accuracy:   {accuracy * 100:.2f}%"
    )

    print(
        f"Macro Precision: {precision * 100:.2f}%"
    )

    print(
        f"Macro Recall:    {recall * 100:.2f}%"
    )

    print(
        f"Macro F1-score:  {f1 * 100:.2f}%"
    )

    print("\nClassification Report:\n")

    print(report)

    print("\nSaved output files:")

    print(MODEL_PATH)
    print(METRICS_PATH)
    print(REPORT_PATH)
    print(CONFUSION_PATH)


if __name__ == "__main__":

    main()
