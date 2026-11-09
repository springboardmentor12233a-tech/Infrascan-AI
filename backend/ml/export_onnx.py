"""
Export trained crack_classifier.pt to crack_classifier.onnx
"""
import os
import sys
import torch
import torch.nn as nn
from torchvision import models
import onnx
import onnxruntime as ort
import numpy as np

# Force utf-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
PT_PATH = os.path.join(MODELS_DIR, "crack_classifier.pt")
ONNX_PATH = os.path.join(MODELS_DIR, "crack_classifier.onnx")

def export():
    print(f"Loading weights from {PT_PATH}...")
    model = models.mobilenet_v3_small(weights=None)
    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 128),
        nn.Hardswish(),
        nn.Dropout(p=0.3),
        nn.Linear(128, 1)
    )
    
    state_dict = torch.load(PT_PATH, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    class InferenceModel(nn.Module):
        def __init__(self, base_model):
            super().__init__()
            self.base_model = base_model

        def forward(self, x):
            logits = self.base_model(x)
            return torch.sigmoid(logits)

    export_model = InferenceModel(model)
    export_model.eval()

    dummy_input = torch.randn(1, 3, 224, 224, dtype=torch.float32)

    print(f"Exporting to {ONNX_PATH}...")
    # Use dynamo=False or legacy torch script export to avoid dynamo unicode print bug
    torch.onnx.export(
        export_model,
        dummy_input,
        ONNX_PATH,
        export_params=True,
        opset_version=18,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["confidence"],
        dynamic_axes={"input": {0: "batch_size"}, "confidence": {0: "batch_size"}}
    )

    print("Checking ONNX model validity...")
    onnx_model = onnx.load(ONNX_PATH)
    onnx.checker.check_model(onnx_model)
    print("ONNX model checker passed!")

    print("Testing with ONNX Runtime...")
    session = ort.InferenceSession(ONNX_PATH)
    sample = np.random.randn(1, 3, 224, 224).astype(np.float32)
    out = session.run(None, {"input": sample})
    print(f"Inference output: {out[0]}")
    print("ONNX Export Successful!")

if __name__ == "__main__":
    export()
