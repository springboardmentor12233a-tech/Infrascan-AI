import sys, os
import os
import cv2
import numpy as np
from PIL import Image

def load_image(image_path: str):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image at {image_path}")
    return image

def rgb_to_bgr(rgb_img):
    return cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)

def bgr_to_rgb(bgr_img):
    return cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)

def save_image(img, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, img)
