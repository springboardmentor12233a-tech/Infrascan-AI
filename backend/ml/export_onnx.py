import os
import sys

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import torch
import torch.nn as nn
from torchvision import models

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
weights_path = os.path.join(MODELS_DIR, "crack_classifier.pt")
onnx_path = os.path.join(MODELS_DIR, "crack_classifier.onnx")

print("Checking trained weights at:", weights_path)
if not os.path.exists(weights_path):
    print("Error: crack_classifier.pt does not exist!")
    exit(1)

model = models.mobilenet_v3_small(weights=None)
in_features = model.classifier[0].in_features
model.classifier = nn.Sequential(
    nn.Linear(in_features, 128),
    nn.Hardswish(),
    nn.Dropout(p=0.3),
    nn.Linear(128, 1)
)

state_dict = torch.load(weights_path, map_location="cpu")
model.load_state_dict(state_dict)
model.eval()

class InferenceModel(nn.Module):
    def __init__(self, base):
        super().__init__()
        self.base = base
    def forward(self, x):
        return torch.sigmoid(self.base(x))

inf_model = InferenceModel(model)
inf_model.eval()

dummy_input = torch.randn(1, 3, 224, 224, dtype=torch.float32)

print("Exporting to ONNX...")
# Use legacy TorchScript based export which is rock-solid across all PyTorch versions
torch.onnx.export(
    inf_model,
    dummy_input,
    onnx_path,
    input_names=["input"],
    output_names=["confidence"],
    opset_version=18,
    dynamo=False
)
print("ONNX export succeeded! File size:", os.path.getsize(onnx_path), "bytes")

import onnxruntime as ort
import numpy as np
session = ort.InferenceSession(onnx_path)
out = session.run(None, {"input": np.random.randn(1, 3, 224, 224).astype(np.float32)})
print("Inference test passed! Output probability:", float(out[0][0][0]))
