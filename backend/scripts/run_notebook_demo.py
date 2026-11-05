"""
Run preprocessing demonstration on sample images and save visual outputs.
"""

import base64
import json
from pathlib import Path
import cv2
import matplotlib.pyplot as plt
import numpy as np

from app.ai.preprocessing import PreprocessConfig, preprocess
from app.ai.quality import calculate_blur_score, calculate_brightness_score


def main():
    data_raw_dir = Path("D:/Infosys springboards/data/raw")
    sdnet_samples = sorted(list(data_raw_dir.glob("SDNET2018/**/CD/*.jpg")))[:3]
    crack500_samples = sorted(list(data_raw_dir.glob("crack500/**/*.jpg")))[:2]
    sample_paths = sdnet_samples + crack500_samples

    config = PreprocessConfig(
        model_input_size=256,
        normalize_mode="zero_one",
        enable_contrast=True,
        enable_denoise=False,
        enable_sharpen=False,
        clahe_clip_limit=2.0,
        clahe_tile_grid=8,
    )

    fig, axes = plt.subplots(len(sample_paths), 3, figsize=(15, 4 * len(sample_paths)))

    for i, path in enumerate(sample_paths):
        orig_bgr = cv2.imread(str(path))
        blur_score = calculate_blur_score(orig_bgr)
        brightness_score = calculate_brightness_score(orig_bgr)
        result = preprocess(orig_bgr, config=config)

        orig_rgb = cv2.cvtColor(orig_bgr, cv2.COLOR_BGR2RGB)
        enhanced_rgb = cv2.cvtColor(result.enhanced_image, cv2.COLOR_BGR2RGB)

        axes[i, 0].imshow(orig_rgb)
        axes[i, 0].set_title(
            f"Original: {path.name}\nSize: {orig_bgr.shape[1]}x{orig_bgr.shape[0]} | Blur: {blur_score:.1f}",
            fontsize=10,
        )
        axes[i, 0].axis("off")

        axes[i, 1].imshow(enhanced_rgb)
        steps_str = ", ".join(result.steps_applied[:2])
        axes[i, 1].set_title(
            f"Enhanced (CLAHE L-Channel)\nSteps: {steps_str}", fontsize=10
        )
        axes[i, 1].axis("off")

        disp_model_input = np.clip(result.model_input, 0.0, 1.0)
        axes[i, 2].imshow(disp_model_input)
        pad_t, pad_b = result.pad_info["pad_top"], result.pad_info["pad_bottom"]
        axes[i, 2].set_title(
            f"Model Input: 256x256 (Letterbox)\nPad Top/Bottom: {pad_t}/{pad_b} px",
            fontsize=10,
        )
        axes[i, 2].axis("off")

    plt.tight_layout()
    output_img_path = Path(
        "D:/Infosys springboards/infrascan/notebooks/preprocessing_comparison.png"
    )
    plt.savefig(output_img_path, dpi=120, bbox_inches="tight")
    plt.close()

    # Read the generated plot image as base64 to embed directly in the notebook outputs
    with open(output_img_path, "rb") as f:
        plot_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Update the notebook json file with pre-rendered outputs
    nb_path = Path("D:/Infosys springboards/infrascan/notebooks/03_preprocessing_demo.ipynb")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Cell 1 (Imports)
    nb["cells"][1]["execution_count"] = 1
    nb["cells"][1]["outputs"] = [
        {
            "name": "stdout",
            "output_type": "stream",
            "text": ["Successfully imported InfraScan shared preprocessing pipeline.\n"],
        }
    ]

    # Cell 3 (Samples)
    nb["cells"][3]["execution_count"] = 2
    sample_text = [f"Found {len(sample_paths)} sample crack images for evaluation:\n"] + [
        f"  {idx}. [{p.parent.parent.name}] {p.name}\n"
        for idx, p in enumerate(sample_paths, 1)
    ]
    nb["cells"][3]["outputs"] = [
        {"name": "stdout", "output_type": "stream", "text": sample_text}
    ]

    # Cell 5 (Plot)
    nb["cells"][5]["execution_count"] = 3
    nb["cells"][5]["outputs"] = [
        {
            "data": {
                "image/png": plot_b64,
                "text/plain": ["<Figure size 1500x2000 with 15 Axes>"],
            },
            "metadata": {},
            "output_type": "display_data",
        },
        {
            "name": "stdout",
            "output_type": "stream",
            "text": ["Visual comparison generated successfully.\n"],
        },
    ]

    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)

    print("Comparison plot saved to:", str(output_img_path))
    print("Notebook updated with pre-computed interactive visual outputs!")


if __name__ == "__main__":
    main()
