
from openvino import convert_model, save_model
from pathlib import Path

saved_model_path = Path("openvino_model/saved_model")
output_path = Path("openvino_model/unet_model.xml")

print("Converting TensorFlow model to OpenVINO...")

model = convert_model(str(saved_model_path))

print("Saving OpenVINO model...")
save_model(model, str(output_path))

print("Conversion completed!")
print("OpenVINO model:", output_path)
