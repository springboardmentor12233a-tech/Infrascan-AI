
import numpy as np
from openvino import Core

core = Core()

print("Available devices:", core.available_devices)

model = core.read_model("openvino_model/unet_model.xml")

print("Loading U-Net on Intel GPU...")

compiled_model = core.compile_model(model, "GPU")

print("U-Net successfully loaded on:", compiled_model.get_property("EXECUTION_DEVICES"))

input_layer = compiled_model.input(0)
output_layer = compiled_model.output(0)

dummy_image = np.random.rand(1, 256, 256, 3).astype(np.float32)

print("Running test prediction...")

result = compiled_model([dummy_image])[output_layer]

print("Prediction completed!")
print("Output shape:", result.shape)
print("Output range:", float(result.min()), "to", float(result.max()))
