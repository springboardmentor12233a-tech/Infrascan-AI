
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[2]

SOURCE = Path(
    r"C:\Users\TANISHKA\Downloads\CrackForest-dataset-master-infrascan-yolo"
    r"\CrackForest-dataset-master"
)

OUTPUT = ROOT / "data" / "segmentation_experiments"

IMAGE_SIZE = (480, 320)

def main():
    versions = {
        "label2_only": {2},
        "label2_plus4": {2, 4}
    }

    for version, crack_labels in versions.items():
        image_dir = OUTPUT / version / "images"
        mask_dir = OUTPUT / version / "masks"

        image_dir.mkdir(parents=True, exist_ok=True)
        mask_dir.mkdir(parents=True, exist_ok=True)

        processed = 0

        for mat_path in sorted(
            (SOURCE / "groundTruth").glob("*.mat")
        ):
            image_path = SOURCE / "image" / f"{mat_path.stem}.jpg"

            if not image_path.exists():
                continue

            annotation = loadmat(mat_path)["groundTruth"][0, 0]
            segmentation = annotation["Segmentation"]

            image = Image.open(image_path).convert("RGB")
            image = image.resize(
                IMAGE_SIZE, Image.Resampling.BILINEAR
            )

            mask_array = (
                np.isin(segmentation, list(crack_labels))
                .astype(np.uint8) * 255
            )

            mask = Image.fromarray(mask_array)

            image.save(image_dir / f"{mat_path.stem}.png")
            mask.save(mask_dir / f"{mat_path.stem}.png")

            processed += 1

        print(f"{version}: {processed} image-mask pairs created")

    print("\nExperimental datasets prepared.")
    print("Output:", OUTPUT)


if __name__ == "__main__":
    main()
