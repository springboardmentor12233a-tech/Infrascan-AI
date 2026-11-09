"""
app/services/inference.py – AI Damage & Crack Assessment Service
Loads the trained ONNX model and executes fast, low-latency defect inference.
"""

import os
import io
import logging
from typing import Dict, Any, Optional
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

ONNX_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ml", "models", "crack_classifier.onnx")
)

_ort_session = None


def get_inference_session():
    global _ort_session
    if _ort_session is None:
        if os.path.exists(ONNX_MODEL_PATH):
            import onnxruntime as ort
            # Run on CPU with optimized threads
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            _ort_session = ort.InferenceSession(ONNX_MODEL_PATH, opts)
            logger.info(f"Loaded ONNX crack assessment model from {ONNX_MODEL_PATH}")
        else:
            logger.warning(f"ONNX model file not found at {ONNX_MODEL_PATH}. Inference disabled.")
    return _ort_session


def preprocess_image_for_model(image_bytes: bytes) -> np.ndarray:
    """
    Decodes image, resizes to 224x224, converts to float32 [0, 1],
    applies standard ImageNet mean/std normalization, and formats as (1, 3, 224, 224).
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        img = img.resize((224, 224), Image.Resampling.BILINEAR)
        img_np = np.array(img, dtype=np.float32) / 255.0

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img_np = (img_np - mean) / std

    # (224, 224, 3) -> (3, 224, 224) -> (1, 3, 224, 224)
    img_np = np.transpose(img_np, (2, 0, 1))
    tensor = np.expand_dims(img_np, axis=0).astype(np.float32)
    return tensor


def classify_damage(image_bytes: bytes) -> Dict[str, Any]:
    """
    Evaluates concrete damage / crack presence on the input image bytes.
    Returns:
      has_crack: bool
      confidence_score: float (0.0 to 1.0)
      severity_level: 'None' | 'Low' | 'Medium' | 'High' | 'Critical'
    """
    session = get_inference_session()
    if session is None:
        return {
            "has_crack": False,
            "confidence_score": 0.0,
            "severity_level": "None",
            "model_ready": False
        }

    tensor = preprocess_image_for_model(image_bytes)
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: tensor})
    
    # Model output is sigmoid probability: shape (1, 1)
    prob = float(outputs[0][0][0])
    prob = max(0.0, min(1.0, prob))

    has_crack = prob >= 0.50

    if prob < 0.50:
        severity = "None"
    elif prob < 0.70:
        severity = "Low"
    elif prob < 0.85:
        severity = "Medium"
    elif prob < 0.95:
        severity = "High"
    else:
        severity = "Critical"

    return {
        "has_crack": has_crack,
        "confidence_score": round(prob, 4),
        "severity_level": severity,
        "model_ready": True
    }


PT_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ml", "models", "crack_classifier.pt")
)
_torch_model = None


def get_torch_model():
    global _torch_model
    if _torch_model is None and os.path.exists(PT_MODEL_PATH):
        try:
            import torch
            import torch.nn as nn
            from torchvision import models

            model = models.mobilenet_v3_small(weights=None)
            in_features = model.classifier[0].in_features
            model.classifier = nn.Sequential(
                nn.Linear(in_features, 128),
                nn.Hardswish(),
                nn.Dropout(p=0.3),
                nn.Linear(128, 1)
            )
            state_dict = torch.load(PT_MODEL_PATH, map_location="cpu")
            model.load_state_dict(state_dict)
            model.eval()
            _torch_model = model
            logger.info("Loaded PyTorch model for Grad-CAM visual explainability.")
        except Exception as e:
            logger.error(f"Failed to load PyTorch model for Grad-CAM: {e}")
    return _torch_model


def generate_gradcam(image_bytes: bytes) -> bytes:
    """
    Computes a Gradient-weighted Class Activation Map (Grad-CAM)
    highlighting the specific spatial defect regions that triggered the model prediction.
    Returns JPEG encoded bytes of the blended original + heatmap image.
    """
    model = get_torch_model()
    if model is None:
        return image_bytes

    try:
        import torch
        import cv2

        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            pil_img = pil_img.convert("RGB")
            orig_w, orig_h = pil_img.size
            orig_np = np.array(pil_img)

        # Preprocess to 224x224
        img_resized = cv2.resize(orig_np, (224, 224)).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        tensor = torch.from_numpy(np.transpose((img_resized - mean) / std, (2, 0, 1))).unsqueeze(0).float()

        activations = []
        gradients = []

        def forward_hook(module, inp, out):
            activations.append(out)

        def backward_hook(module, grad_in, grad_out):
            gradients.append(grad_out[0])

        target_layer = model.features[-1]
        h_f = target_layer.register_forward_hook(forward_hook)
        h_b = target_layer.register_full_backward_hook(backward_hook)

        model.zero_grad()
        logit = model(tensor)
        logit.backward()

        h_f.remove()
        h_b.remove()

        if not activations or not gradients:
            return image_bytes

        grads = gradients[0].detach()
        acts = activations[0].detach()

        # Global average pool the gradients
        weights = grads.mean(dim=(2, 3), keepdim=True)
        cam = (weights * acts).sum(dim=1, keepdim=True)
        cam = torch.relu(cam).squeeze().numpy()

        cam_min, cam_max = cam.min(), cam.max()
        if cam_max - cam_min > 1e-8:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            cam = np.zeros_like(cam)

        cam_resized = cv2.resize(cam, (orig_w, orig_h))
        heatmap = cv2.applyColorMap(np.uint8(255 * cam_resized), cv2.COLORMAP_JET)
        heatmap_rgb = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

        # 60% original image + 40% Grad-CAM heatmap
        overlay = cv2.addWeighted(orig_np, 0.60, heatmap_rgb, 0.40, 0)

        # Encode back to JPEG
        is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
        if is_success:
            return buffer.tobytes()
        return image_bytes
    except Exception as e:
        logger.error(f"Grad-CAM generation error: {e}")
        return image_bytes

