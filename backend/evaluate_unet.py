
from pathlib import Path
import numpy as np
from PIL import Image
from tensorflow.keras.models import load_model

# Load trained U-Net model
MODEL_PATH = Path("models/InfraScan_UNet_Improved_BCE_Dice.keras")
model = load_model(str(MODEL_PATH), compile=False)

IMAGE_DIR = Path("all_test_images")
LABEL_DIR = Path("all_test_labels")

dice_scores = []
iou_scores = []
matched = 0

# Find all test images
image_files = sorted(
    p for p in IMAGE_DIR.iterdir()
    if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
)

# Match each image with its actual mask using the filename
for image_path in image_files:
    label_path = next(
        (p for p in LABEL_DIR.glob("*")
         if p.stem == image_path.stem),
        None
    )

    if label_path is None:
        print("Mask not found for:", image_path.name)
        continue

    # Load and preprocess original image
    image = Image.open(image_path).convert("RGB")
    image = image.resize((256, 256))
    image_array = np.array(image, dtype=np.float32) / 255.0
    image_array = np.expand_dims(image_array, axis=0)

    # Predict crack mask
    prediction = model.predict(image_array, verbose=0)[0]
    predicted_mask = prediction[:, :, 0] > 0.5

    # Load actual ground-truth mask
    actual_image = Image.open(label_path).convert("L")
    actual_image = actual_image.resize(
        (256, 256), Image.Resampling.NEAREST
    )
    actual_mask = np.array(actual_image) > 127

    # Calculate Dice and IoU
    intersection = np.logical_and(
        predicted_mask, actual_mask
    ).sum()

    union = np.logical_or(
        predicted_mask, actual_mask
    ).sum()

    dice = (
        2 * intersection /
        (predicted_mask.sum() + actual_mask.sum() + 1e-8)
    )

    iou = intersection / (union + 1e-8)

    dice_scores.append(dice)
    iou_scores.append(iou)
    matched += 1

    print(f"Processed: {image_path.name}")

# Display final results
print("\n========== U-Net Evaluation Results ==========")
print("Total test images found:", len(image_files))
print("Images successfully evaluated:", matched)

if matched > 0:
    print("Average Dice Score:",
          round(np.mean(dice_scores) * 100, 2), "%")
    print("Average IoU Score:",
          round(np.mean(iou_scores) * 100, 2), "%")
else:
    print("No matching image and mask pairs were found.")
