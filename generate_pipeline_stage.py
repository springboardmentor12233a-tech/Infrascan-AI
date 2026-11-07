import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_IMAGE = os.path.join(SCRIPT_DIR, "datasets", "Positive", "00001.jpg")
FIGURES_DIR = os.path.join(SCRIPT_DIR, "reports", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

if not os.path.exists(SAMPLE_IMAGE):
    raise FileNotFoundError(f"Sample positive image not found at: {SAMPLE_IMAGE}")

img_bgr = cv2.imread(SAMPLE_IMAGE)
img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

# Quality assessment metric (Laplacian variance)
lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

# Bilateral denoising (noise suppression)
denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

# CLAHE enhancement (adaptive histogram equalization)
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
clahe_img = clahe.apply(denoised)

# Crack boundary gradient enhancement (Canny edge filter)
edges = cv2.Canny(clahe_img, 40, 120)

fig, axes = plt.subplots(1, 4, figsize=(12, 3.2), dpi=300)

axes[0].imshow(img_rgb)
axes[0].set_title(f"(a) Raw Image\n(Sharpness: Var={lap_var:.1f})", fontsize=9.5, fontweight='bold', color="#1F4E79")
axes[0].axis('off')

axes[1].imshow(denoised, cmap='gray')
axes[1].set_title("(b) Bilateral Denoised\n(Noise Suppressed)", fontsize=9.5, fontweight='bold', color="#1F4E79")
axes[1].axis('off')

axes[2].imshow(clahe_img, cmap='gray')
axes[2].set_title("(c) CLAHE Enhanced\n(Adaptive Equalization)", fontsize=9.5, fontweight='bold', color="#1F4E79")
axes[2].axis('off')

axes[3].imshow(edges, cmap='gray')
axes[3].set_title("(d) Crack Boundary Map\n(Gradient Response)", fontsize=9.5, fontweight='bold', color="#1F4E79")
axes[3].axis('off')

plt.suptitle("Figure 1: InfraScan Image Quality Assessment & Preprocessing Stages", fontsize=11, fontweight='bold', color="#1F4E79", y=1.03)
plt.tight_layout()

save_path = os.path.join(FIGURES_DIR, "preprocessing_stages.png")
plt.savefig(save_path, dpi=300, bbox_inches='tight')
plt.close()
print("Saved pipeline stages to:", save_path)
