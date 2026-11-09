"""
InfraScan Enhanced EDA Runner
Executes comprehensive dataset analysis:
1. Fixes class labeling for SDNET2018 ('Non-cracked' -> Uncracked)
2. Laplacian blur score distribution (justifies blur threshold in backend)
3. Brightness and contrast analysis (justifies CLAHE preprocessing)
4. Infrastructure-specific defect ratio (Decks vs Pavements vs Walls)
5. Generates publication-ready figures in outputs/eda
"""

import os
import glob
import json
import random
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

# Directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATASET_DIR = os.path.join(PROJECT_ROOT, "backend", "ml", "dataset")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "eda")
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 60)
print("       INFRASCAN: ENHANCED EDA & STRUCTURAL ANALYSIS       ")
print("=" * 60)
print(f"Scanning dataset in: {DATASET_DIR}")

# 1. Dataset Scan & Label Resolution
records = []
valid_exts = {".jpg", ".jpeg", ".png"}

for root, dirs, files in os.walk(DATASET_DIR):
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in valid_exts:
            rel = os.path.relpath(root, DATASET_DIR)
            parts_lower = [p.lower() for p in rel.replace("\\", "/").split("/")]
            
            # Accurate label matching including 'non-cracked'
            if any(p in {"c", "crack", "cracked", "positive"} for p in parts_lower):
                label = "Cracked"
            elif any(p in {"u", "non-crack", "non_crack", "non-cracked", "non_cracked", "uncracked", "un-cracked", "negative"} for p in parts_lower):
                label = "Uncracked"
            else:
                label = "Unknown"

            # Infrastructure type
            if any(p in {"d", "deck", "decks"} for p in parts_lower):
                infra = "Bridge Deck"
            elif any(p in {"w", "wall", "walls"} for p in parts_lower):
                infra = "Concrete Wall"
            elif any(p in {"p", "pavement", "pavements"} for p in parts_lower):
                infra = "Pavement"
            else:
                infra = "Other"

            records.append({
                "path": os.path.join(root, f),
                "filename": f,
                "folder": rel,
                "label": label,
                "infrastructure": infra
            })

df = pd.DataFrame(records)
print(f"Total images scanned: {len(df)}")
print("\nAccurate Class Distribution:")
class_counts = df["label"].value_counts()
print(class_counts)

# Save inventory
inventory_csv = os.path.join(OUTPUT_DIR, "sdnet2018_corrected_inventory.csv")
df.to_csv(inventory_csv, index=False)
print(f"Saved inventory: {inventory_csv}")

# Chart 1: Corrected Class Distribution
plt.figure(figsize=(7, 5))
colors = ["#10b981", "#ef4444"] if list(class_counts.index) == ["Uncracked", "Cracked"] else ["#ef4444", "#10b981"]
bars = plt.bar(class_counts.index, class_counts.values, color=colors, width=0.5, edgecolor="black", alpha=0.85)
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2.0, yval + 500, f"{yval:,} ({yval/len(df)*100:.1f}%)", ha="center", va="bottom", fontweight="bold")
plt.title("SDNET2018 Corrected Class Distribution (Cracked vs. Uncracked)", fontsize=12, fontweight="bold")
plt.ylabel("Number of Images", fontsize=11)
plt.ylim(0, max(class_counts.values) * 1.15)
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
chart1_path = os.path.join(OUTPUT_DIR, "sdnet2018_class_distribution_corrected.png")
plt.savefig(chart1_path, dpi=200)
plt.close()
print(f"Saved chart: {chart1_path}")

# Chart 2: Defect Rate by Infrastructure Type
infra_table = pd.crosstab(df["infrastructure"], df["label"])
infra_pct = pd.crosstab(df["infrastructure"], df["label"], normalize="index") * 100
print("\nInfrastructure Defect Breakdown:")
print(infra_table)
print("\nDefect Percentages:")
print(infra_pct.round(2))

plt.figure(figsize=(8, 5))
ax = infra_pct[["Uncracked", "Cracked"]].plot(kind="bar", stacked=True, color=["#10b981", "#ef4444"], edgecolor="black", alpha=0.85, figsize=(8, 5))
plt.title("Crack Defect Ratio by Infrastructure Asset Type", fontsize=12, fontweight="bold")
plt.ylabel("Percentage (%)", fontsize=11)
plt.xlabel("Civil Infrastructure Category", fontsize=11)
plt.xticks(rotation=0)
plt.legend(["Uncracked (Healthy)", "Cracked (Defect)"], loc="upper right")
for p in ax.patches:
    width, height = p.get_width(), p.get_height()
    if height > 5:
        ax.text(p.get_x() + width/2, p.get_y() + height/2, f"{height:.1f}%", ha="center", va="center", color="white", fontweight="bold")
plt.tight_layout()
chart2_path = os.path.join(OUTPUT_DIR, "sdnet2018_infrastructure_defect_ratio.png")
plt.savefig(chart2_path, dpi=200)
plt.close()
print(f"Saved chart: {chart2_path}")

# 2. Sample 1,000 images (500 cracked, 500 uncracked) for Computer Vision Analysis
print("\nSampling 1,000 images for blur, brightness & contrast analysis...")
cracked_sample = df[df["label"] == "Cracked"].sample(n=min(500, len(df[df["label"] == "Cracked"])), random_state=42)
uncracked_sample = df[df["label"] == "Uncracked"].sample(n=min(500, len(df[df["label"] == "Uncracked"])), random_state=42)
cv_sample = pd.concat([cracked_sample, uncracked_sample])

blur_scores = []
brightness_scores = []
contrast_scores = []

for _, row in cv_sample.iterrows():
    img_bgr = cv2.imread(row["path"])
    if img_bgr is None:
        continue
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Laplacian variance blur score
    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    # Mean luminance brightness
    brightness = float(np.mean(gray))
    # Standard deviation contrast
    contrast = float(np.std(gray))
    
    blur_scores.append(blur)
    brightness_scores.append(brightness)
    contrast_scores.append(contrast)

cv_sample["blur_score"] = blur_scores
cv_sample["brightness"] = brightness_scores
cv_sample["contrast"] = contrast_scores

# Chart 3: Blur Score Distribution (Laplacian Variance)
plt.figure(figsize=(9, 5))
cracked_blur = cv_sample[cv_sample["label"] == "Cracked"]["blur_score"]
uncracked_blur = cv_sample[cv_sample["label"] == "Uncracked"]["blur_score"]

plt.hist(np.clip(uncracked_blur, 0, 1500), bins=35, alpha=0.6, color="#10b981", label=f"Uncracked (Median: {uncracked_blur.median():.1f})", edgecolor="white")
plt.hist(np.clip(cracked_blur, 0, 1500), bins=35, alpha=0.6, color="#ef4444", label=f"Cracked (Median: {cracked_blur.median():.1f})", edgecolor="white")
plt.axvline(x=100.0, color="#d97706", linestyle="--", linewidth=2, label="InfraScan Low-Quality Threshold (100.0)")

plt.title("Image Sharpness Analysis: Laplacian Variance Distribution", fontsize=12, fontweight="bold")
plt.xlabel("Laplacian Variance (Sharpness Score)", fontsize=11)
plt.ylabel("Number of Sample Images", fontsize=11)
plt.legend(loc="upper right")
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
chart3_path = os.path.join(OUTPUT_DIR, "sdnet2018_blur_score_distribution.png")
plt.savefig(chart3_path, dpi=200)
plt.close()
print(f"Saved chart: {chart3_path}")

# Chart 4: Brightness & Contrast Distribution
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Brightness
ax1.hist(cv_sample[cv_sample["label"] == "Cracked"]["brightness"], bins=25, alpha=0.6, color="#ef4444", label="Cracked", edgecolor="white")
ax1.hist(cv_sample[cv_sample["label"] == "Uncracked"]["brightness"], bins=25, alpha=0.6, color="#10b981", label="Uncracked", edgecolor="white")
ax1.set_title("Luminance / Brightness Distribution", fontweight="bold")
ax1.set_xlabel("Mean Grayscale Value (0=Black, 255=White)")
ax1.set_ylabel("Count")
ax1.legend()
ax1.grid(axis="y", linestyle="--", alpha=0.5)

# Contrast
ax2.hist(cv_sample[cv_sample["label"] == "Cracked"]["contrast"], bins=25, alpha=0.6, color="#ef4444", label="Cracked", edgecolor="white")
ax2.hist(cv_sample[cv_sample["label"] == "Uncracked"]["contrast"], bins=25, alpha=0.6, color="#10b981", label="Uncracked", edgecolor="white")
ax2.set_title("Surface Contrast Distribution (Std Dev)", fontweight="bold")
ax2.set_xlabel("Pixel Std Deviation (Texture Variation)")
ax2.legend()
ax2.grid(axis="y", linestyle="--", alpha=0.5)

plt.suptitle("Concrete Surface Photometric Properties (Empirical CLAHE Justification)", fontsize=13, fontweight="bold")
plt.tight_layout()
chart4_path = os.path.join(OUTPUT_DIR, "sdnet2018_brightness_contrast_distribution.png")
plt.savefig(chart4_path, dpi=200)
plt.close()
print(f"Saved chart: {chart4_path}")

print("\n" + "=" * 60)
print("SUCCESS: Enhanced EDA executed! All 4 analytical charts saved.")
print(f"Output directory: {OUTPUT_DIR}")
print("=" * 60)
