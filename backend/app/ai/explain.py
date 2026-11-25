"""Explainable AI (XAI) service module for InfraScan.

Pure computational functions (no database access) providing:
1. Grad-CAM & Grad-CAM++ for crack segmentation (SMP UnetPlusPlus ResNet-34) on model.encoder.layer4[-1]
2. Captum Saliency on crack probability
3. EigenCAM for YOLO and RT-DETR distress detectors on the pre-head feature layer
4. Map similarity helper (Spearman rank correlation and top 10% overlap)
5. Color overlay generation with alpha blending (JET colormap)

Deterministic: eval mode, seed 42, no dropout.
"""

from dataclasses import dataclass
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np
import torch
import torch.nn as nn
from captum.attr import Saliency
from pytorch_grad_cam import EigenCAM, GradCAM, GradCAMPlusPlus
from pytorch_grad_cam.utils.model_targets import SemanticSegmentationTarget
from scipy.stats import spearmanr


# Dummy target for EigenCAM (EigenCAM is gradient-free and does not use classification targets)
class _DummyEigenTarget:
    def __call__(self, model_output: Any) -> float:
        return 0.0


@dataclass
class ExplanationOutput:
    """Container for explanation results."""
    heatmap: np.ndarray             # 2D float32 array in range [0.0, 1.0] at original image resolution
    overlay_png: bytes              # Encoded PNG bytes of the alpha-blended JET colormap
    metadata: Dict[str, Any]        # Method, target layer, timings, scale, warnings


def _set_deterministic(seed: int = 42) -> None:
    """Set random seeds for reproducible explanations."""
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)


def generate_color_overlay(
    img_bgr: np.ndarray,
    heatmap: np.ndarray,
    alpha: float = 0.5,
    colormap: int = cv2.COLORMAP_JET,
) -> Tuple[np.ndarray, bytes]:
    """
    Generate an alpha-blended color overlay over an image using JET colormap.
    Returns (overlay_bgr, png_bytes).
    """
    orig_h, orig_w = img_bgr.shape[:2]
    if heatmap.shape[:2] != (orig_h, orig_w):
        heatmap = cv2.resize(heatmap, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

    # Normalize heatmap strictly to 0..255 uint8
    norm_heat = np.clip(heatmap * 255.0, 0, 255).astype(np.uint8)
    colored_cam = cv2.applyColorMap(norm_heat, colormap)

    # Alpha blend: overlay = (1 - alpha) * img + alpha * cam
    overlay = cv2.addWeighted(img_bgr, 1.0 - alpha, colored_cam, alpha, 0)
    success, png_bytes = cv2.imencode(".png", overlay)
    if not success:
        raise RuntimeError("Failed to encode explanation overlay to PNG format.")
    return overlay, png_bytes.tobytes()


def compare_maps(map_a: np.ndarray, map_b: np.ndarray) -> Dict[str, Any]:
    """
    Compute Spearman rank correlation and top 10% spatial overlap between two heatmaps.
    """
    if map_a.shape != map_b.shape:
        map_b = cv2.resize(map_b, (map_a.shape[1], map_a.shape[0]), interpolation=cv2.INTER_LINEAR)

    flat_a = map_a.flatten().astype(np.float64)
    flat_b = map_b.flatten().astype(np.float64)

    # Spearman rank correlation
    corr, p_val = spearmanr(flat_a, flat_b)
    if np.isnan(corr):
        corr = 0.0
    if np.isnan(p_val):
        p_val = 1.0

    # Top 10% highest attention regions
    p90_a = np.percentile(flat_a, 90)
    p90_b = np.percentile(flat_b, 90)
    top_a = map_a >= p90_a
    top_b = map_b >= p90_b

    intersection = int(np.logical_and(top_a, top_b).sum())
    union = int(np.logical_or(top_a, top_b).sum())
    iou = float(intersection / union) if union > 0 else 0.0

    interpretation = (
        "Strong agreement" if corr > 0.7
        else "Moderate agreement" if corr > 0.4
        else "Low or divergent agreement"
    )

    return {
        "spearman_correlation": float(round(corr, 4)),
        "p_value": float(round(p_val, 6)),
        "top_10_overlap": float(round(iou, 4)),
        "interpretation": interpretation,
    }


def explain_segmentation(
    model: nn.Module,
    img_bgr: np.ndarray,
    method: str = "gradcam",
    threshold: float = 0.40,
    max_side: int = 1280,
    model_name: str = "unetplusplus_crack500",
) -> ExplanationOutput:
    """
    Explain semantic crack segmentation prediction using Grad-CAM, Grad-CAM++, or Captum Saliency.
    Target layer: model.encoder.layer4[-1]
    Target output: Predicted crack mask or top 1% highest probability pixels if mask is empty.
    """
    _set_deterministic(42)
    start_time = time.time()
    warnings_list: List[str] = []

    method_norm = method.lower().replace("-", "").replace("_", "")
    if method_norm not in ("gradcam", "gradcampp", "gradcamplusplus", "saliency"):
        raise ValueError(
            f"Unsupported segmentation explanation method '{method}'. "
            f"Supported methods are: ['gradcam', 'gradcampp', 'saliency']."
        )

    # 1. Check target layer existence
    if not hasattr(model, "encoder") or not hasattr(model.encoder, "layer4"):
        raise ValueError("Model does not possess the expected 'encoder.layer4' attribute for ResNet-34.")
    target_layer = model.encoder.layer4[-1]
    target_layer_name = f"model.encoder.layer4[-1] ({target_layer.__class__.__name__})"

    model.eval()

    orig_h, orig_w = img_bgr.shape[:2]

    # 2. Scale image if exceeding max_side like the analysis runner
    max_dim = max(orig_h, orig_w)
    if max_dim > max_side:
        scale_ratio = max_side / float(max_dim)
        infer_w = int(round(orig_w * scale_ratio))
        infer_h = int(round(orig_h * scale_ratio))
        img_bgr_infer = cv2.resize(img_bgr, (infer_w, infer_h), interpolation=cv2.INTER_AREA)
        is_scaled = True
    else:
        infer_w = orig_w
        infer_h = orig_h
        img_bgr_infer = img_bgr
        is_scaled = False

    img_rgb_infer = cv2.cvtColor(img_bgr_infer, cv2.COLOR_BGR2RGB)

    # 3. Reflection padding to multiple of 32
    pad_h = (32 - (infer_h % 32)) % 32
    pad_w = (32 - (infer_w % 32)) % 32
    if pad_h > 0 or pad_w > 0:
        img_padded = cv2.copyMakeBorder(
            img_rgb_infer.astype(np.float32), 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT_101
        )
    else:
        img_padded = img_rgb_infer.astype(np.float32)

    # ImageNet normalization: mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    norm_img = (img_padded / 255.0 - mean) / std

    tensor = torch.from_numpy(norm_img.transpose(2, 0, 1)).unsqueeze(0).float()

    # 4. Compute predicted probability map and target mask
    with torch.no_grad():
        logits = model(tensor)
        probs_padded = torch.sigmoid(logits).squeeze().cpu().numpy()

    probs_unpadded = probs_padded[:infer_h, :infer_w]
    bin_mask = (probs_unpadded > threshold).astype(np.float32)

    if bin_mask.sum() == 0:
        k = max(1, int(probs_unpadded.size * 0.01))
        top1_thresh = float(np.partition(probs_unpadded.flatten(), -k)[-k])
        bin_mask = (probs_unpadded >= top1_thresh).astype(np.float32)
        target_desc = f"Top 1% crack probability pixels (empty mask fallback, threshold={top1_thresh:.4f})"
        warnings_list.append("Predicted crack mask was empty; explained top 1% most probable pixels.")
    else:
        target_desc = f"Predicted crack mask (binary, threshold={threshold:.2f})"

    # Prepare padded target mask matching tensor spatial dimensions
    target_mask_padded = np.zeros((infer_h + pad_h, infer_w + pad_w), dtype=np.float32)
    target_mask_padded[:infer_h, :infer_w] = bin_mask

    # 5. Compute explanation map
    if method_norm in ("gradcam", "gradcampp", "gradcamplusplus"):
        cam_class = GradCAMPlusPlus if "pp" in method_norm or "plus" in method_norm else GradCAM
        targets = [SemanticSegmentationTarget(category=0, mask=target_mask_padded)]

        with cam_class(model=model, target_layers=[target_layer]) as cam:
            raw_cam = cam(input_tensor=tensor, targets=targets)[0]

        # Crop out padding
        cam_cropped = raw_cam[:infer_h, :infer_w]
        min_before = float(cam_cropped.min())
        max_before = float(cam_cropped.max())

    elif method_norm == "saliency":
        # Plain input-gradient saliency on crack probability
        # Compute at reduced size for CPU speed if image is large
        sal_max_side = 512
        if max(infer_h, infer_w) > sal_max_side:
            sal_ratio = sal_max_side / float(max(infer_h, infer_w))
            sal_w = int(round(infer_w * sal_ratio))
            sal_h = int(round(infer_h * sal_ratio))
            sal_img = cv2.resize(img_rgb_infer, (sal_w, sal_h), interpolation=cv2.INTER_AREA)
            # Re-pad for 32 multiple
            sal_pad_h = (32 - (sal_h % 32)) % 32
            sal_pad_w = (32 - (sal_w % 32)) % 32
            sal_padded = cv2.copyMakeBorder(sal_img.astype(np.float32), 0, sal_pad_h, 0, sal_pad_w, cv2.BORDER_REFLECT_101)
            sal_norm = (sal_padded / 255.0 - mean) / std
            sal_tensor = torch.from_numpy(sal_norm.transpose(2, 0, 1)).unsqueeze(0).float()
            sal_mask = cv2.resize(bin_mask, (sal_w, sal_h), interpolation=cv2.INTER_NEAREST)
            sal_mask_pad = np.zeros((sal_h + sal_pad_h, sal_w + sal_pad_w), dtype=np.float32)
            sal_mask_pad[:sal_h, :sal_w] = sal_mask
            sal_mask_tensor = torch.from_numpy(sal_mask_pad).unsqueeze(0).unsqueeze(0)
            use_sal_tensor = sal_tensor
            use_sal_mask = sal_mask_tensor
            crop_h, crop_w = sal_h, sal_w
        else:
            use_sal_tensor = tensor.clone()
            use_sal_mask = torch.from_numpy(target_mask_padded).unsqueeze(0).unsqueeze(0)
            crop_h, crop_w = infer_h, infer_w

        class _CrackProbModel(nn.Module):
            def __init__(self, seg_model, mask_tensor):
                super().__init__()
                self.seg_model = seg_model
                self.register_buffer("mask", mask_tensor)

            def forward(self, x):
                logits = self.seg_model(x)
                probs = torch.sigmoid(logits)
                return (probs * self.mask).sum(dim=(1, 2, 3), keepdim=True)

        prob_wrapper = _CrackProbModel(model, use_sal_mask)
        saliency_attr = Saliency(prob_wrapper)
        use_sal_tensor.requires_grad = True
        grads = saliency_attr.attribute(use_sal_tensor)

        # Max absolute gradient across RGB channels
        raw_sal = grads.squeeze(0).abs().max(dim=0)[0].detach().cpu().numpy()
        sal_cropped = raw_sal[:crop_h, :crop_w]
        if crop_h != infer_h or crop_w != infer_w:
            cam_cropped = cv2.resize(sal_cropped, (infer_w, infer_h), interpolation=cv2.INTER_LINEAR)
        else:
            cam_cropped = sal_cropped

        min_before = float(cam_cropped.min())
        max_before = float(cam_cropped.max())

    # 6. Map back to original image size if inference was scaled
    if is_scaled:
        heatmap_orig = cv2.resize(cam_cropped, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
    else:
        heatmap_orig = cam_cropped

    # 7. Strictly normalize to range [0.0, 1.0] per image
    h_min = float(heatmap_orig.min())
    h_max = float(heatmap_orig.max())
    if h_max > h_min:
        heatmap_final = (heatmap_orig - h_min) / (h_max - h_min)
    else:
        heatmap_final = np.zeros_like(heatmap_orig)
    heatmap_final = np.clip(heatmap_final, 0.0, 1.0).astype(np.float32)

    # 8. Generate color overlay PNG
    _, overlay_png = generate_color_overlay(img_bgr, heatmap_final)

    elapsed = round(time.time() - start_time, 3)

    metadata = {
        "model_name": model_name,
        "method": method_norm,
        "target_layer": target_layer_name,
        "target_description": target_desc,
        "image_size": [orig_w, orig_h],
        "inference_size": [infer_w, infer_h],
        "min_before_normalisation": round(min_before, 6),
        "max_before_normalisation": round(max_before, 6),
        "normalised_per_image": True,
        "seconds": elapsed,
        "warnings": warnings_list,
    }

    return ExplanationOutput(
        heatmap=heatmap_final,
        overlay_png=overlay_png,
        metadata=metadata,
    )


def explain_detector(
    detector_model: Any,
    img_bgr: np.ndarray,
    model_class: str = "yolo",
    method: str = "eigencam",
    imgsz: int = 640,
    max_side: int = 1280,
    model_name: str = "yolov8s_rdd2022",
) -> ExplanationOutput:
    """
    Explain object detector (YOLO or RT-DETR) predictions using EigenCAM on the last feature layer.
    Preprocesses with exact Ultralytics aspect-ratio letterboxing, then maps back to original image size.
    For RT-DETR, marks method as experimental and records status in metadata.
    """
    _set_deterministic(42)
    start_time = time.time()
    warnings_list: List[str] = []

    method_norm = method.lower().replace("-", "").replace("_", "")
    if method_norm != "eigencam":
        raise ValueError(
            f"Unsupported detector explanation method '{method}'. "
            f"Supported methods for object detectors are: ['eigencam']."
        )

    # Extract underlying PyTorch nn.Module from Ultralytics wrapper
    if hasattr(detector_model, "model") and isinstance(detector_model.model, nn.Module):
        model_module = detector_model.model
    elif isinstance(detector_model, nn.Module):
        model_module = detector_model
    else:
        raise TypeError(f"Expected Ultralytics model or PyTorch nn.Module, got {type(detector_model)}")

    model_module.eval()

    orig_h, orig_w = img_bgr.shape[:2]

    # Pre-scale if max_side is exceeded like analysis runner
    max_dim = max(orig_h, orig_w)
    if max_dim > max_side:
        scale_ratio = max_side / float(max_dim)
        proc_w = int(round(orig_w * scale_ratio))
        proc_h = int(round(orig_h * scale_ratio))
        img_bgr_proc = cv2.resize(img_bgr, (proc_w, proc_h), interpolation=cv2.INTER_AREA)
    else:
        proc_w = orig_w
        proc_h = orig_h
        img_bgr_proc = img_bgr

    # Identify target layer right before detection head
    # In YOLO DetectionModel: head is model.model[-1] (Detect), target layer is model.model[-2]
    # In RT-DETR DetectionModel: head is model.model[-1] (RTDETRDecoder), target layer is model.model[-2]
    is_rtdetr = "rtdetr" in str(model_class).lower() or "rtdetr" in str(detector_model.__class__.__name__).lower()

    if hasattr(model_module, "model") and hasattr(model_module.model, "__len__") and len(model_module.model) >= 2:
        target_layer = model_module.model[-2]
        target_layer_idx = len(model_module.model) - 2
        target_layer_name = f"model.model[{target_layer_idx}] ({target_layer.__class__.__name__})"
    else:
        # Fallback to last convolutional / residual block
        conv_candidates = [m for m in model_module.modules() if isinstance(m, (nn.Conv2d, nn.Sequential))]
        if not conv_candidates:
            raise ValueError("Could not automatically locate feature layer before detector head.")
        target_layer = conv_candidates[-2] if len(conv_candidates) >= 2 else conv_candidates[-1]
        target_layer_name = f"fallback ({target_layer.__class__.__name__})"

    if is_rtdetr:
        warnings_list.append("RT-DETR EigenCAM explanation is experimental (attention-based decoder).")

    # Letterbox preprocessing (same as Ultralytics inference)
    scale = min(imgsz / float(proc_h), imgsz / float(proc_w))
    new_unpad_w = int(round(proc_w * scale))
    new_unpad_h = int(round(proc_h * scale))
    pad_w = (imgsz - new_unpad_w) / 2.0
    pad_h = (imgsz - new_unpad_h) / 2.0

    resized = cv2.resize(img_bgr_proc, (new_unpad_w, new_unpad_h), interpolation=cv2.INTER_LINEAR)
    top = int(round(pad_h - 0.1))
    bottom = int(round(pad_h + 0.1))
    left = int(round(pad_w - 0.1))
    right = int(round(pad_w + 0.1))

    # Pad with gray 114
    letterboxed = cv2.copyMakeBorder(
        resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114)
    )

    # Convert to RGB, normalize 0..1, transpose to (1, 3, imgsz, imgsz)
    letterboxed_rgb = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2RGB)
    input_tensor = (
        torch.from_numpy(letterboxed_rgb.transpose(2, 0, 1))
        .unsqueeze(0)
        .float()
        / 255.0
    )

    # Compute EigenCAM
    with EigenCAM(model=model_module, target_layers=[target_layer]) as cam:
        cam_map = cam(input_tensor=input_tensor, targets=[_DummyEigenTarget()])[0]

    min_before = float(cam_map.min())
    max_before = float(cam_map.max())

    # Unpad letterbox region
    cam_unpad = cam_map[top : top + new_unpad_h, left : left + new_unpad_w]

    # Map back to original image size
    heatmap_orig = cv2.resize(cam_unpad, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

    # Strictly normalize to 0..1
    h_min = float(heatmap_orig.min())
    h_max = float(heatmap_orig.max())
    if h_max > h_min:
        heatmap_final = (heatmap_orig - h_min) / (h_max - h_min)
    else:
        heatmap_final = np.zeros_like(heatmap_orig)
    heatmap_final = np.clip(heatmap_final, 0.0, 1.0).astype(np.float32)

    # Generate color overlay PNG
    _, overlay_png = generate_color_overlay(img_bgr, heatmap_final)

    elapsed = round(time.time() - start_time, 3)

    metadata = {
        "model_name": model_name,
        "method": "eigencam",
        "target_layer": target_layer_name,
        "target_description": f"EigenCAM on pre-head feature layer ({target_layer.__class__.__name__})",
        "image_size": [orig_w, orig_h],
        "inference_size": [imgsz, imgsz],
        "min_before_normalisation": round(min_before, 6),
        "max_before_normalisation": round(max_before, 6),
        "normalised_per_image": True,
        "seconds": elapsed,
        "experimental": is_rtdetr,
        "rtdetr_ran": is_rtdetr,
        "warnings": warnings_list,
    }

    return ExplanationOutput(
        heatmap=heatmap_final,
        overlay_png=overlay_png,
        metadata=metadata,
    )
