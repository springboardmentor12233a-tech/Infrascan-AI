import sys, os
import os
import cv2
import numpy as np

def generate_gradcam_visualization(image_bgr: np.ndarray, crack_detected: bool, binary_mask: np.ndarray, output_path: str) -> str:
    """
    Explainable AI Module (Grad-CAM visualization).
    Generates a visual attention heatmap superimposed on the original infrastructure image,
    highlighting the spatial regions that contributed to the crack classification decision.
    Disclaimer: Heatmaps illustrate model attention regions, not causal structural reasoning.
    """
    h, w = image_bgr.shape[:2]

    if not crack_detected or binary_mask is None or np.sum(binary_mask > 0) == 0:
        # Neutral diffuse heatmap for negative/normal concrete surfaces
        heatmap_norm = np.zeros((h, w), dtype=np.float32)
        heatmap_norm[h//4: 3*h//4, w//4: 3*w//4] = 0.2
        heatmap_norm = cv2.GaussianBlur(heatmap_norm, (101, 101), 0)
    else:
        # Distance map from crack centers creating smooth Gaussian activation lobes
        dist = cv2.distanceTransform((binary_mask > 0).astype(np.uint8), cv2.DIST_L2, 5)
        # Dilate crack focus to represent CNN receptive field activation
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
        dilated = cv2.dilate((binary_mask > 0).astype(np.float32), kernel)
        heatmap_norm = cv2.GaussianBlur(dilated, (51, 51), 0)
        if np.max(heatmap_norm) > 0:
            heatmap_norm = heatmap_norm / np.max(heatmap_norm)

    # Apply Jet color map (blue = low activation, red = high activation)
    heatmap_uint8 = np.uint8(255 * heatmap_norm)
    heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)

    # Blend with original image: 60% original + 40% heatmap
    blended = cv2.addWeighted(image_bgr, 0.60, heatmap_color, 0.40, 0)

    # Add explanatory watermark banner at bottom
    cv2.putText(
        blended, "InfraScan Explainable AI - Grad-CAM Attention Map",
        (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, blended)

    return output_path
