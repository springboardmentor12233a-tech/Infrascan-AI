from pathlib import Path
import random
import matplotlib.pyplot as plt
from PIL import Image

# Locate the dataset folder
DATASET_DIR = Path(__file__).resolve().parent.parent / "datasets"

# Dataset categories
categories = ["Positive", "Negative"]

random.seed(42)

# Create a figure with 6 image positions
fig, axes = plt.subplots(2, 3, figsize=(12, 8))

for row, category in enumerate(categories):
    folder = DATASET_DIR / category
    images = list(folder.glob("*.jpg"))

    # Select 3 random images
    samples = random.sample(images, min(3, len(images)))

    for col, image_path in enumerate(samples):
        with Image.open(image_path) as image:
            axes[row, col].imshow(image.convert("RGB"))

        axes[row, col].set_title(category)
        axes[row, col].axis("off")

plt.suptitle("InfraScan: Concrete Crack Dataset Samples")
plt.tight_layout()
plt.show()
