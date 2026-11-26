import sys, os
import cv2
import numpy as np

def assess_image_quality(image_bgr: np.ndarray) -> dict:
    """
    Performs comprehensive image quality assessment matching Milestone 2 methodology:
    - Blur score using variance of Laplacian
    - Brightness mean
    - Contrast standard deviation
    - Resolution validation
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Blur score
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    is_blurry = laplacian_var < 100.0

    # Brightness
    brightness_mean = float(np.mean(gray))
    is_low_light = brightness_mean < 50.0

    # Contrast
    contrast_std = float(np.std(gray))

    # Resolution validation
    resolution_ok = (w >= 256 and h >= 256)

    return {
        "blur_score": round(laplacian_var, 2),
        "is_blurry": is_blurry,
        "brightness_mean": round(brightness_mean, 2),
        "is_low_light": is_low_light,
        "contrast_std": round(contrast_std, 2),
        "image_width": int(w),
        "image_height": int(h),
        "resolution_ok": resolution_ok
    }
