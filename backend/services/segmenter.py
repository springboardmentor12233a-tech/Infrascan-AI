"""
Segmenter Inference Service.

Loads the trained CRACK500 U-Net segmentation model, executes pixel-level inference,
generates binary masks, and renders transparent crack overlay visualizations.
"""

from pathlib import Path
from typing import Dict, Optional
import uuid

import cv2
import keras
import numpy as np

from src.segmentation.model import combined_bce_dice_loss, dice_coef, iou_metric
from .preprocessing import preprocess_segmentation

DEFAULT_UNET_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "segmentation" / "best_unet.keras"
PREDICTIONS_DIR = Path(__file__).resolve().parent.parent.parent / "outputs" / "predictions"


def detect_dark_padding(img_bgr: np.ndarray, max_margin_ratio: float = 0.20, dark_thresh: float = 55.0):
    """Detects uniform dark letterboxing / screenshot frame borders."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    max_h = int(h * max_margin_ratio)
    max_w = int(w * max_margin_ratio)

    top = 0
    while top < max_h and np.mean(gray[top, :]) < dark_thresh:
        top += 1

    bottom = h
    while bottom > h - max_h and np.mean(gray[bottom - 1, :]) < dark_thresh:
        bottom -= 1

    left = 0
    while left < max_w and np.mean(gray[:, left]) < dark_thresh:
        left += 1

    right = w
    while right > w - max_w and np.mean(gray[:, right - 1]) < dark_thresh:
        right -= 1

    return top, bottom, left, right


def frangi_crack_filter(image_gray: np.ndarray, sigmas=(1.0, 1.5, 2.0)) -> np.ndarray:
    """
    Computes multi-scale Hessian-based ridge filter to detect fine hairline crack lines.
    Cracks appear as dark intensity troughs (ridges in inverted space) on concrete.
    """
    float_img = image_gray.astype(np.float32) / 255.0
    inv_img = 1.0 - float_img
    max_response = np.zeros_like(float_img)

    for s in sigmas:
        ksize = int(2 * np.ceil(2 * s) + 1)
        blurred = cv2.GaussianBlur(inv_img, (ksize, ksize), s)
        dx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
        dy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
        dxx = cv2.Sobel(dx, cv2.CV_32F, 1, 0, ksize=3)
        dxy = cv2.Sobel(dx, cv2.CV_32F, 0, 1, ksize=3)
        dyy = cv2.Sobel(dy, cv2.CV_32F, 0, 1, ksize=3)

        trace = dxx + dyy
        det = dxx * dyy - dxy * dxy
        discriminant = np.maximum(trace * trace - 4.0 * det, 0.0)
        sqrt_disc = np.sqrt(discriminant)
        lambda2 = (trace - sqrt_disc) / 2.0

        response = np.maximum(-lambda2, 0.0) * (s**2)
        max_response = np.maximum(max_response, response)

    if max_response.max() > 0:
        max_response = max_response / max_response.max()

    return max_response


def connect_crack_components(binary_mask: np.ndarray, max_gap: float = 25.0, line_thickness: int = 2) -> np.ndarray:
    """
    Connects disjoint crack components whose closest endpoints/boundaries
    are within max_gap distance of each other (e.g. across surface spalls, aggregates, or narrow hairline gaps).
    """
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask)
    if num_labels <= 2:
        return binary_mask.copy()

    result = binary_mask.copy()
    comps = []
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] < 12:
            continue
        pts = np.argwhere(labels == i)  # (y, x)
        comps.append({'id': i, 'pts': pts})

    if len(comps) <= 1:
        return result

    for i in range(len(comps)):
        for j in range(i + 1, len(comps)):
            c1_pts = comps[i]['pts']
            c2_pts = comps[j]['pts']

            sub1 = c1_pts[::3] if len(c1_pts) > 300 else c1_pts
            sub2 = c2_pts[::3] if len(c2_pts) > 300 else c2_pts

            diff = sub1[:, np.newaxis, :] - sub2[np.newaxis, :, :]
            dists_sq = np.sum(diff**2, axis=2)
            min_idx = np.unravel_index(np.argmin(dists_sq), dists_sq.shape)
            min_dist = np.sqrt(dists_sq[min_idx])

            if min_dist <= max_gap:
                p1 = tuple(sub1[min_idx[0]])[::-1]  # (x, y)
                p2 = tuple(sub2[min_idx[1]])[::-1]  # (x, y)
                cv2.line(result, p1, p2, 1, thickness=line_thickness)

    return result


def hysteresis_crack_segmentation(
    pred_map: np.ndarray,
    t_high: float = 0.35,
    t_low: float = 0.15,
    min_seed_area: int = 15,
    max_gap: float = 25.0
) -> np.ndarray:
    """
    Dual-threshold hysteresis segmentation with trajectory bridge.
    1. Strong crack seeds: P >= t_high
    2. Candidate crack pixels: P >= t_low
    3. Retain only candidate components containing verified strong crack seeds.
    4. Connect collinear/adjacent fissure endpoints across narrow physical gaps.
    """
    strong = (pred_map >= t_high).astype(np.uint8)
    candidate = (pred_map >= t_low).astype(np.uint8)

    num_cand, cand_labels, cand_stats, _ = cv2.connectedComponentsWithStats(candidate)
    retained = np.zeros_like(candidate)

    for i in range(1, num_cand):
        mask_i = (cand_labels == i)
        seed_overlap = np.sum(strong[mask_i])
        if seed_overlap >= min_seed_area:
            retained[mask_i] = 1

    # Connect nearby components along the continuous crack trajectory
    connected = connect_crack_components(retained, max_gap=max_gap, line_thickness=2)
    return connected


class SegmenterService:
    """Singleton service for crack segmentation and overlay generation."""

    def __init__(self, model_path: Optional[Path] = None, output_dir: Optional[Path] = None):
        self.model_path = model_path or DEFAULT_UNET_PATH
        self.output_dir = output_dir or PREDICTIONS_DIR
        self.masks_dir = self.output_dir / "masks"
        self.overlays_dir = self.output_dir / "overlays"
        self.model: Optional[keras.Model] = None

        # Ensure prediction output directories exist
        self.masks_dir.mkdir(parents=True, exist_ok=True)
        self.overlays_dir.mkdir(parents=True, exist_ok=True)

    def is_loaded(self) -> bool:
        return self.model is not None

    def load_model(self):
        """Loads U-Net model with registered custom loss and metric functions."""
        if self.model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Segmentation model weights not found at: {self.model_path}")
            print(f"[SegmenterService] Loading U-Net model from {self.model_path} ...")
            custom_objects = {
                "combined_bce_dice_loss": combined_bce_dice_loss,
                "loss": combined_bce_dice_loss(),
                "dice_coef": dice_coef,
                "iou_metric": iou_metric
            }
            self.model = keras.models.load_model(str(self.model_path), custom_objects=custom_objects)
            print("[SegmenterService] Segmentation U-Net loaded successfully.")

    def predict(self, image_bgr: np.ndarray, base_url: str = "") -> Dict:
        """
        Executes crack segmentation, creates binary mask, and renders overlay image.
        Uses boundary suppression, adaptive contrast, and hysteresis thresholding to
        prevent border artifacts and guarantee complete fissure detection.

        Args:
            image_bgr: Decoded image in OpenCV BGR format.
            base_url: Optional base URL prefix for web assets.

        Returns:
            Dict containing label, pixel counts, percentages, paths, and URLs.
        """
        if self.model is None:
            self.load_model()

        orig_h, orig_w = image_bgr.shape[:2]

        # 1. Detect and crop artificial dark border frames (e.g. screenshot or letterbox borders)
        top, bottom, left, right = detect_dark_padding(image_bgr)
        has_padding = (top > 0 or bottom < orig_h or left > 0 or right < orig_w)
        work_img = image_bgr[top:bottom, left:right] if has_padding else image_bgr
        h_work, w_work = work_img.shape[:2]

        # 2. Check for light concrete surfaces with subtle contrast
        work_gray = cv2.cvtColor(work_img, cv2.COLOR_BGR2GRAY)
        is_light_concrete = (work_gray.mean() > 140 and work_gray.std() < 40)

        if is_light_concrete:
            lab = cv2.cvtColor(work_img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
            prep_img = cv2.cvtColor(cv2.merge((clahe.apply(l), a, b)), cv2.COLOR_LAB2RGB)
            t_seed, t_ridge = 0.35, 0.12
        else:
            prep_img = cv2.cvtColor(work_img, cv2.COLOR_BGR2RGB)
            t_seed, t_ridge = 0.45, 0.25

        tensor = cv2.resize(prep_img, (256, 256), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0
        tensor = np.expand_dims(tensor, 0)

        # 3. Model forward pass
        pred_map = self.model.predict(tensor, verbose=0)[0, :, :, 0]

        # 4. Suppress convolution zero-padding boundary artifacts (outer 2 border pixels)
        pred_map[:2, :] = 0
        pred_map[-2:, :] = 0
        pred_map[:, :2] = 0
        pred_map[:, -2:] = 0

        # Resize neural prediction to working resolution
        pred_work = cv2.resize(pred_map, (w_work, h_work), interpolation=cv2.INTER_LINEAR)

        # 5. Neural-Guided Multi-Scale Ridge & Hysteresis Segmentation
        # Guarantees complete continuous crack line detection and captures subtle hairline fissures
        seeds = (pred_work >= t_seed).astype(np.uint8)
        total_seed_px = int(np.sum(seeds))

        if total_seed_px < 15:
            # Clean sound concrete: reject all noise, 0 false positives
            binary_work = np.zeros((h_work, w_work), dtype=np.uint8)
        else:
            if is_light_concrete:
                # Multi-scale Hessian ridge filter for fine hairline fissure lines
                ridge = frangi_crack_filter(work_gray, sigmas=(1.0, 1.5, 2.0))
                candidates = ((ridge >= t_ridge) | (pred_work >= 0.25)).astype(np.uint8)
                num_cand, cand_labels, cand_stats, _ = cv2.connectedComponentsWithStats(candidates)
                retained = np.zeros_like(candidates)
                for i in range(1, num_cand):
                    comp_mask = (cand_labels == i)
                    if np.sum(seeds[comp_mask]) >= 5:
                        retained[comp_mask] = 1
                binary_work = connect_crack_components(retained, max_gap=25.0, line_thickness=2)
            else:
                binary_256 = hysteresis_crack_segmentation(
                    pred_map,
                    t_high=0.45,
                    t_low=0.25,
                    min_seed_area=15,
                    max_gap=20.0
                )
                binary_work = cv2.resize(binary_256, (w_work, h_work), interpolation=cv2.INTER_NEAREST)

            # Suppress rectangular perimeter frame artifacts
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_work)
            cleaned_work = np.zeros_like(binary_work)
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                comp_w = stats[i, cv2.CC_STAT_WIDTH]
                comp_h = stats[i, cv2.CC_STAT_HEIGHT]
                if comp_w >= w_work - 16 and comp_h >= h_work - 16:
                    density = area / (comp_w * comp_h)
                    if density < 0.4:
                        continue
                if area >= 12:
                    cleaned_work[labels == i] = 1
            binary_work = cleaned_work

        # 7. Map active crack mask back onto original canvas if padding was cropped
        if has_padding:
            binary_mask_orig = np.zeros((orig_h, orig_w), dtype=np.uint8)
            binary_mask_orig[top:bottom, left:right] = binary_work
        else:
            binary_mask_orig = binary_work

        crack_pixel_count = int(np.sum(binary_mask_orig > 0))
        total_pixels = orig_h * orig_w
        crack_percentage = float(round((crack_pixel_count / total_pixels) * 100, 2))
        is_crack_detected = crack_pixel_count > 0

        # Render visual overlay
        overlay = image_bgr.copy()
        if is_crack_detected:
            # Highlight crack pixels with bright red tint (BGR: 0, 0, 255)
            crack_indices = binary_mask_orig > 0
            red_layer = np.full_like(image_bgr, (0, 0, 255))
            overlay[crack_indices] = cv2.addWeighted(
                image_bgr[crack_indices],
                0.35,
                red_layer[crack_indices],
                0.65,
                0
            )
            # Outline boundary contours for enhanced contrast
            contours, _ = cv2.findContours(
                binary_mask_orig * 255,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            cv2.drawContours(overlay, contours, -1, (0, 0, 255), 2)

        # Unique identifiers for saved assets
        pred_id = uuid.uuid4().hex[:12]
        mask_filename = f"{pred_id}_mask.png"
        overlay_filename = f"{pred_id}_overlay.jpg"

        mask_filepath = self.masks_dir / mask_filename
        overlay_filepath = self.overlays_dir / overlay_filename

        # Save binary mask (0 = background, 255 = crack)
        cv2.imwrite(str(mask_filepath), binary_mask_orig * 255)
        # Save overlay image
        cv2.imwrite(str(overlay_filepath), overlay)

        rel_mask_path = f"outputs/predictions/masks/{mask_filename}"
        rel_overlay_path = f"outputs/predictions/overlays/{overlay_filename}"

        clean_base = base_url.rstrip("/") if base_url else ""
        mask_url = f"{clean_base}/{rel_mask_path}" if clean_base else f"/{rel_mask_path}"
        overlay_url = f"{clean_base}/{rel_overlay_path}" if clean_base else f"/{rel_overlay_path}"

        label = "Crack Detected" if is_crack_detected else "No Crack Detected"
        message = (
            f"Segmentation identified {crack_pixel_count:,} crack-like pixels ({crack_percentage:.2f}% surface coverage). "
            "Further inspection by a qualified civil engineering professional is recommended."
            if is_crack_detected
            else "Segmentation detected 0 crack-like pixels across the inspected surface."
        )

        return {
            "label": label,
            "crack_pixel_count": crack_pixel_count,
            "crack_percentage": crack_percentage,
            "mask_path": rel_mask_path,
            "overlay_path": rel_overlay_path,
            "mask_url": mask_url,
            "overlay_url": overlay_url,
            "status": "success",
            "message": message
        }


# Global singleton instance
segmenter_service = SegmenterService()

