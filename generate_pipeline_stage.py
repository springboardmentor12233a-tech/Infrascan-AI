import cv2
import numpy as np
import matplotlib.pyplot as plt

img_bgr = cv2.imread(r"F:\Infosys Intern 7.0\InfraScan\Infrascan-AI\datasets\Positive\00001.jpg")
img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

# Quality assessment metric
lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

# Bilateral denoising
denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

# CLAHE enhancement
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
clahe_img = clahe.apply(denoised)

# Crack boundary gradient enhancement
edges = cv2.Canny(clahe_img, 40, 120)

fig, axes = plt.subplots(1, 4, figsize=(12, 3.2), dpi=300)

axes[0].imshow(img_rgb)
axes[0].set_title("(a) Raw Image\n(Sharpness: Var={:.1f})".format(lap_var), fontsize=9.5, fontweight='bold', color="#1F4E79")
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

save_path = r"F:\Infosys Intern 7.0\InfraScan\Infrascan-AI\reports\figures\preprocessing_stages.png"
plt.savefig(save_path, dpi=300, bbox_inches='tight')
plt.close()
print("Saved pipeline stages to:", save_path)
