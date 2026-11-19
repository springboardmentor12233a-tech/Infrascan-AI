
import tensorflow as tf
from pathlib import Path

model_path = Path("models/InfraScan_UNet_Improved_BCE_Dice.keras")
export_path = Path("openvino_model/saved_model")

print("Loading existing U-Net model...")

model = tf.keras.models.load_model(
    model_path,
    compile=False
)

print("Exporting model to SavedModel format...")

model.export(str(export_path))

print("Export completed!")
print("SavedModel location:", export_path)
