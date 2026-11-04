
import numpy as np
from PIL import Image

# Load predicted mask
predicted = Image.open("predicted_crack_mask.png").convert("L")

# Load actual ground-truth mask
actual = Image.open("test_labels/11125-1.png").convert("L")

# Resize actual mask to match predicted mask dimensions
actual = actual.resize(predicted.size, Image.Resampling.NEAREST)

# Convert images into binary masks
predicted = np.array(predicted) > 127
actual = np.array(actual) > 127

# Calculate intersection and union
intersection = np.logical_and(predicted, actual).sum()
union = np.logical_or(predicted, actual).sum()

# Calculate Dice Score
dice = (2 * intersection) / (predicted.sum() + actual.sum() + 1e-8)

# Calculate IoU
iou = intersection / (union + 1e-8)

print("Dice Score:", round(dice * 100, 2), "%")
print("IoU Score:", round(iou * 100, 2), "%")
