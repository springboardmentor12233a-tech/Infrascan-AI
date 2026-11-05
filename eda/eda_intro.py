from pathlib import Path
from collections import Counter

# 1. Define the dataset location
DATASET_DIR = Path(__file__).resolve().parent.parent / "datasets"

# 2. Define the two categories
categories = ["Positive", "Negative"]

print("=" * 50)
print("       INFRASCAN - DATASET ANALYSIS")
print("=" * 50)

total_images = 0

# 3. Count images in each category
for category in categories:
    folder = DATASET_DIR / category

    if not folder.exists():
        print(f"ERROR: Folder not found: {folder}")
        continue

    images = [
        file for file in folder.iterdir()
        if file.is_file()
        and file.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
    ]

    count = len(images)
    total_images += count

    print(f"\nCategory: {category}")
    print(f"Number of images: {count}")

    # Check image formats
    formats = Counter(
        image.suffix.lower() for image in images
    )
    print(f"Image formats: {dict(formats)}")

# 4. Display the total
print("\n" + "=" * 50)
print(f"TOTAL IMAGES: {total_images}")
print("=" * 50)

