from pathlib import Path
from collections import Counter
from PIL import Image, UnidentifiedImageError

# Locate the dataset
DATASET_DIR = Path(__file__).resolve().parent.parent / "datasets"
categories = ["Positive", "Negative"]

dimension_counts = Counter()
format_counts = Counter()
total_images = 0
unreadable_images = []

print("=" * 55)
print("       INFRASCAN - IMAGE QUALITY CHECK")
print("=" * 55)

for category in categories:
    folder = DATASET_DIR / category
    image_files = [
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
    ]

    print(f"\nChecking {category} images...")

    for image_path in image_files:
        try:
            with Image.open(image_path) as image:
                dimension_counts[image.size] += 1
                format_counts[image.format] += 1
                total_images += 1

        except (OSError, UnidentifiedImageError):
            unreadable_images.append(str(image_path))

print("\n--- RESULTS ---")
print(f"Readable images: {total_images}")
print(f"Unreadable images: {len(unreadable_images)}")

print("\nImage dimensions (width, height):")
for dimensions, count in dimension_counts.most_common():
    print(f"{dimensions}: {count} images")

print("\nImage formats:")
for image_format, count in format_counts.items():
    print(f"{image_format}: {count} images")

if unreadable_images:
    print("\nExamples of unreadable images:")
    for path in unreadable_images[:10]:
        print(path)

print("\nImage quality check completed.")
