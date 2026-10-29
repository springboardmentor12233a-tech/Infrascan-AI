from pathlib import Path
from collections import Counter

DATASET_PATH = (
    Path.home()
    / "Downloads"
    / "DATA_Maguire_20180517_ALL"
    / "DATA_Maguire_20180517_ALL"
    / "SDNET2018"
)

image_extensions = {".jpg", ".jpeg", ".png", ".webp"}

print("SDNET2018 Dataset Analysis")
print("-" * 35)

if not DATASET_PATH.exists():
    print("Dataset folder not found!")
    print(f"Current path: {DATASET_PATH}")
    print("Please check the dataset location.")

else:
    all_images = [
        file for file in DATASET_PATH.rglob("*")
        if file.is_file()
        and file.suffix.lower() in image_extensions
    ]

    print(f"Total images: {len(all_images)}")

    print("\nFolder Analysis")
    print("-" * 35)

    for folder in sorted(DATASET_PATH.iterdir()):
        if folder.is_dir():
            images = [
                file for file in folder.rglob("*")
                if file.is_file()
                and file.suffix.lower() in image_extensions
            ]
            print(f"{folder.name}: {len(images)} images")

    print("\nSubfolder Analysis")
    print("-" * 35)

    for folder in sorted(DATASET_PATH.iterdir()):
        if folder.is_dir():
            print(f"\n{folder.name}:")
            for subfolder in sorted(folder.iterdir()):
                if subfolder.is_dir():
                    count = sum(
                        1 for file in subfolder.rglob("*")
                        if file.is_file()
                        and file.suffix.lower() in image_extensions
                    )
                    print(f"  {subfolder.name}: {count} images")




import random
import matplotlib.pyplot as plt
from PIL import Image

if DATASET_PATH.exists():
    all_images = [
        file for file in DATASET_PATH.rglob("*")
        if file.is_file()
        and file.suffix.lower() in image_extensions
    ]

    if all_images:
        sample_images = random.sample(
            all_images, min(6, len(all_images))
        )

        fig, axes = plt.subplots(2, 3, figsize=(12, 8))

        for ax, image_path in zip(axes.flat, sample_images):
            with Image.open(image_path) as img:
                ax.imshow(img.convert("RGB"))

            ax.set_title(image_path.parent.name)
            ax.axis("off")

        plt.tight_layout()
        plt.show()
    else:
        print("No images found to display.")


from PIL import Image

if DATASET_PATH.exists():
    dimension_counts = Counter()
    checked = 0
    errors = 0

    for image_path in DATASET_PATH.rglob("*"):
        if image_path.is_file() and image_path.suffix.lower() in image_extensions:
            try:
                with Image.open(image_path) as img:
                    dimension_counts[img.size] += 1
                checked += 1
            except Exception:
                errors += 1

    print("\nImage Dimension Analysis")
    print("-" * 30)
    print(f"Images checked: {checked}")
    print(f"Unreadable images: {errors}")
    print("Most common dimensions:")

    for size, count in dimension_counts.most_common(10):
        print(f"{size[0]} x {size[1]}: {count} images")




if DATASET_PATH.exists():
    print("\nCracked vs Uncracked Image Count")
    print("-" * 35)

    class_folders = {
        "Cracked Deck": DATASET_PATH / "D" / "CD",
        "Uncracked Deck": DATASET_PATH / "D" / "UD",
        "Cracked Pavement": DATASET_PATH / "P" / "CP",
        "Uncracked Pavement": DATASET_PATH / "P" / "UP",
        "Cracked Wall": DATASET_PATH / "W" / "CW",
        "Uncracked Wall": DATASET_PATH / "W" / "UW",
    }

    for label, folder in class_folders.items():
        if folder.exists():
            count = sum(
                1 for file in folder.rglob("*")
                if file.is_file()
                and file.suffix.lower() in image_extensions
            )
            print(f"{label}: {count}")
        else:
            print(f"{label}: Folder not found")





            import matplotlib.pyplot as plt

labels = [
    "Cracked Deck",
    "Uncracked Deck",
    "Cracked Pavement",
    "Uncracked Pavement",
    "Cracked Wall",
    "Uncracked Wall"
]

counts = [2025, 11595, 2608, 21726, 3851, 14287]

plt.figure(figsize=(10, 5))
plt.bar(labels, counts)
plt.title("SDNET2018 Class Distribution")
plt.xlabel("Image Class")
plt.ylabel("Number of Images")
plt.xticks(rotation=35, ha="right")
plt.tight_layout()
plt.show()


print("\nClass Imbalance Percentages")
print("-" * 35)

cracked = 2025 + 2608 + 3851
uncracked = 11595 + 21726 + 14287
total = cracked + uncracked

print(f"Cracked: {cracked} ({cracked / total * 100:.2f}%)")
print(f"Uncracked: {uncracked} ({uncracked / total * 100:.2f}%)")
print(f"Total images: {total}")





