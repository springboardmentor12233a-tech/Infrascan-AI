from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt

DATA_DIR = Path("dataset/split_data/train")

classes = ["D_CD", "D_UD", "P_CP", "P_UP", "W_CW", "W_UW"]

fig, axes = plt.subplots(6, 4, figsize=(12, 16))

for row, class_name in enumerate(classes):
    folder = DATA_DIR / class_name
    images = sorted(folder.glob("*.jpg"))[:4]

    for col, image_path in enumerate(images):
        image = Image.open(image_path)
        axes[row, col].imshow(image)
        axes[row, col].set_title(class_name if col == 0 else image_path.name)
        axes[row, col].axis("off")

plt.tight_layout()
plt.savefig("backend/models/m3_class_samples.png", dpi=150)
plt.show()