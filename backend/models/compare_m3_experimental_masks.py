
from pathlib import Path
import matplotlib.pyplot as plt
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "segmentation_experiments"

image_id = "084"

original = Image.open(
    BASE / "label2_only" / "images" / f"{image_id}.png"
).convert("RGB")

mask_a = Image.open(
    BASE / "label2_only" / "masks" / f"{image_id}.png"
).convert("L")

mask_b = Image.open(
    BASE / "label2_plus4" / "masks" / f"{image_id}.png"
).convert("L")

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

axes[0].imshow(original)
axes[0].set_title("Original Image")

axes[1].imshow(mask_a, cmap="gray")
axes[1].set_title("Version A: Label 2")

axes[2].imshow(mask_b, cmap="gray")
axes[2].set_title("Version B: Labels 2 + 4")

for ax in axes:
    ax.axis("off")

plt.tight_layout()

output = ROOT / "backend" / "models" / "m3_mask_experiment_comparison.png"
plt.savefig(output, dpi=150)
plt.show()

print("Saved:", output)
