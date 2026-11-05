from pathlib import Path
from PIL import Image, ImageOps

PROCESSED_DIR = Path(__file__).parent.parent / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def preprocess_image(image_path):
    image = Image.open(image_path)

    # Correct image orientation
    image = ImageOps.exif_transpose(image)

    # Convert to RGB
    image = image.convert("RGB")

    # Resize while maintaining aspect ratio
    image.thumbnail((1024, 1024))

    # Normalize pixel values
    normalized = image.point(lambda pixel: pixel / 255 * 255)

    # Save processed image
    output_path = PROCESSED_DIR / f"processed_{Path(image_path).stem}.jpg"
    normalized.save(output_path, format="JPEG", quality=90)

    return {
        "processed_path": str(output_path),
        "width": normalized.width,
        "height": normalized.height,
        "format": "JPEG",
        "status": "success"
    }