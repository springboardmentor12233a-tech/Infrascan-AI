import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURES_DIR = os.path.join(SCRIPT_DIR, "reports", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

# 1. Model Performance Comparison Chart
plt.figure(figsize=(9, 5), dpi=300)
metrics = [
    ("Classification\nAccuracy", 99.69, "#1F4E79"),
    ("Classification\nF1-Score", 99.70, "#1F4E79"),
    ("Detection\nPrecision", 64.20, "#2E75B6"),
    ("Detection\nmAP@50", 58.60, "#2E75B6"),
    ("Segmentation\nPixel Acc.", 97.80, "#41719C"),
    ("Segmentation\nDice (F1)", 54.21, "#41719C"),
    ("Segmentation\nMean IoU", 40.54, "#41719C"),
]

names = [m[0] for m in metrics]
values = [m[1] for m in metrics]
colors = [m[2] for m in metrics]

bars = plt.bar(names, values, color=colors, width=0.55, edgecolor="#143452", linewidth=1.2, zorder=3)

for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width() / 2.0, yval + 1.2, f"{yval:.2f}%", 
             ha='center', va='bottom', fontsize=9.5, fontweight='bold', color="#1F4E79")

plt.ylim(0, 115)
plt.ylabel("Performance Metric (%)", fontsize=11, fontweight='bold', color="#1F4E79")
plt.title("InfraScan Milestone 2: Evaluated Computer Vision Model Performance", fontsize=12, fontweight='bold', color="#1F4E79", pad=14)
plt.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
plt.axhline(100, color='gray', linestyle=':', linewidth=0.8, alpha=0.7)

# Custom legend
legend_elements = [
    Patch(facecolor="#1F4E79", edgecolor="#143452", label='Binary Classification (CCIC 40k)'),
    Patch(facecolor="#2E75B6", edgecolor="#143452", label='YOLOv8 Detection (Road Defects)'),
    Patch(facecolor="#41719C", edgecolor="#143452", label='U-Net Segmentation (CFD/Crack500)')
]
plt.legend(handles=legend_elements, loc='upper right', framealpha=0.9, fontsize=8.5)

plt.tight_layout()
chart_path = os.path.join(FIGURES_DIR, "model_performance_comparison.png")
plt.savefig(chart_path, dpi=300)
plt.close()
print("Saved:", chart_path)

# 2. Confusion Matrix Heatmap
plt.figure(figsize=(6, 5), dpi=300)
cm = np.array([[3988, 12],
               [13, 3987]])

plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
plt.title("Confusion Matrix: Binary Crack Classification (Test Set: N=8,000)", fontsize=11, fontweight='bold', color="#1F4E79", pad=12)
plt.colorbar(fraction=0.046, pad=0.04)
tick_marks = np.arange(2)
classes = ['Negative (No Crack)', 'Positive (Crack)']
plt.xticks(tick_marks, classes, fontsize=9.5, fontweight='bold')
plt.yticks(tick_marks, classes, fontsize=9.5, fontweight='bold', rotation=90, va='center')

thresh = cm.max() / 2.
for i in range(2):
    for j in range(2):
        plt.text(j, i, f"{cm[i, j]:,}\n({cm[i, j]/4000*100:.2f}%)",
                 ha="center", va="center",
                 color="white" if cm[i, j] > thresh else "#1F4E79",
                 fontsize=11, fontweight='bold')

plt.ylabel('Ground Truth Class', fontsize=10.5, fontweight='bold', color="#1F4E79")
plt.xlabel('Model Predicted Class', fontsize=10.5, fontweight='bold', color="#1F4E79")
plt.tight_layout()

cm_path = os.path.join(FIGURES_DIR, "confusion_matrix_classification.png")
plt.savefig(cm_path, dpi=300)
plt.close()
print("Saved:", cm_path)
