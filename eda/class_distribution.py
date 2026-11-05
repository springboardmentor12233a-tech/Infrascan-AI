from pathlib import Path
import matplotlib.pyplot as plt

# Locate the dataset
DATASET_DIR = Path(__file__).resolve().parent.parent / "datasets"

# Count images in each category
categories = ["Positive", "Negative"]
counts = []

for category in categories:
    folder = DATASET_DIR / category

    image_count = sum(
        1 for file in folder.iterdir()
        if file.is_file()
        and file.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
    )

    counts.append(image_count)

# Calculate percentages
total = sum(counts)

print("CLASS DISTRIBUTION")
print("-" * 30)

for category, count in zip(categories, counts):
    percentage = count / total * 100 if total else 0
    print(f"{category}: {count} images ({percentage:.2f}%)")

# Create bar chart
plt.figure(figsize=(8, 5))

bars = plt.bar(categories, counts)

plt.title("InfraScan - Concrete Crack Dataset Distribution")
plt.xlabel("Image Category")
plt.ylabel("Number of Images")
plt.bar_label(bars, fmt="%.0f")

plt.tight_layout()

# Save the chart
output_path = Path(__file__).resolve().parent / "class_distribution.png"
plt.savefig(output_path, dpi=300)

print(f"\nChart saved to: {output_path}")

plt.show()
