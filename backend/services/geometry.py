import sys, os
import cv2
import numpy as np

def extract_crack_geometry(binary_mask: np.ndarray, is_calibrated: bool = False, scale_mm_per_px: float = None) -> dict:
    """
    Extracts geometric properties from a binary crack mask (0 or 255):
    - Crack area (px)
    - Crack skeleton length (px)
    - Mean and max crack width (px)
    - Crack density (%)
    - Crack orientation angle (degrees)
    - Branching / connected components count
    """
    mask_binary = (binary_mask > 127).astype(np.uint8)
    total_surface_pixels = mask_binary.shape[0] * mask_binary.shape[1]
    crack_area_px = int(np.sum(mask_binary))

    if crack_area_px == 0:
        return {
            "crack_area_px": 0,
            "crack_area_ratio": 0.0,
            "skeleton_length_px": 0.0,
            "mean_width_px": 0.0,
            "max_width_px": 0.0,
            "crack_density": 0.0,
            "orientation_angle": 0.0,
            "num_branches": 0,
            "num_components": 0,
            "is_calibrated": is_calibrated,
            "scale_mm_per_px": scale_mm_per_px,
            "estimated_length_mm": None,
            "estimated_max_width_mm": None
        }

    # Crack density
    crack_density = float((crack_area_px / total_surface_pixels) * 100.0)
    crack_area_ratio = float(crack_area_px / total_surface_pixels)

    # Skeletonization using morphological thinning
    # OpenCV ximgproc or standard morphological skeleton
    size = np.size(mask_binary)
    skel = np.zeros(mask_binary.shape, np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    temp_img = mask_binary.copy() * 255

    for _ in range(50):
        eroded = cv2.erode(temp_img, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(temp_img, temp)
        skel = cv2.bitwise_or(skel, temp)
        temp_img = eroded.copy()
        if cv2.countNonZero(temp_img) == 0:
            break

    skeleton_length_px = float(cv2.countNonZero(skel))

    # Crack width via distance transform
    dist_transform = cv2.distanceTransform(mask_binary * 255, cv2.DIST_L2, 5)
    skel_coords = np.where(skel > 0)
    if len(skel_coords[0]) > 0:
        widths = dist_transform[skel_coords] * 2.0 # diameter approximation
        mean_width_px = float(np.mean(widths))
        max_width_px = float(np.max(widths))
    else:
        mean_width_px = float(crack_area_px / max(skeleton_length_px, 1.0))
        max_width_px = mean_width_px * 1.5

    # Connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask_binary)
    num_components = max(0, num_labels - 1)

    # Orientation angle of dominant crack component via PCA / moments
    orientation_angle = 0.0
    y_idx, x_idx = np.where(mask_binary > 0)
    if len(x_idx) > 5:
        coords = np.column_stack([x_idx, y_idx]).astype(np.float32)
        mean, eigenvectors = cv2.PCACompute(coords, mean=np.empty((0)))
        angle_rad = np.arctan2(eigenvectors[0, 1], eigenvectors[0, 0])
        orientation_angle = float(np.degrees(angle_rad))
        if orientation_angle < 0:
            orientation_angle += 180.0

    # Branch points approximation
    # A skeleton pixel with more than 2 neighbors in 3x3 is typically a junction/branch
    kernel = np.ones((3, 3), np.uint8)
    neighbor_count = cv2.filter2D((skel > 0).astype(np.uint8), -1, kernel) - 1
    branches = np.logical_and(skel > 0, neighbor_count >= 3)
    num_branches = int(np.sum(branches))

    # Physical measurements if calibrated
    est_length_mm = None
    est_max_width_mm = None
    if is_calibrated and scale_mm_per_px and scale_mm_per_px > 0:
        est_length_mm = round(skeleton_length_px * scale_mm_per_px, 2)
        est_max_width_mm = round(max_width_px * scale_mm_per_px, 2)

    return {
        "crack_area_px": crack_area_px,
        "crack_area_ratio": round(crack_area_ratio, 6),
        "skeleton_length_px": round(skeleton_length_px, 2),
        "mean_width_px": round(mean_width_px, 2),
        "max_width_px": round(max_width_px, 2),
        "crack_density": round(crack_density, 3),
        "orientation_angle": round(orientation_angle, 1),
        "num_branches": num_branches,
        "num_components": num_components,
        "is_calibrated": is_calibrated,
        "scale_mm_per_px": scale_mm_per_px,
        "estimated_length_mm": est_length_mm,
        "estimated_max_width_mm": est_max_width_mm
    }
