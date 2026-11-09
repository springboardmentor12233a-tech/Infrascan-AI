"""
backend/ml/download_second_dataset.py
Downloads and prepares the METU Concrete Crack Benchmark Dataset (Özgenel et al.)
Used in dual-dataset training alongside SDNET2018.
"""

import os
import zipfile
import urllib.request

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "second_dataset")

URLS = {
    "validation": "https://huggingface.co/datasets/mohammadnajeeb/concrete_crack_images/resolve/main/data/validation.zip",
    "test": "https://huggingface.co/datasets/mohammadnajeeb/concrete_crack_images/resolve/main/data/test.zip",
}


def download_and_extract():
    os.makedirs(DATASET_DIR, exist_ok=True)
    for split, url in URLS.items():
        zip_path = os.path.join(DATASET_DIR, f"{split}.zip")
        if not os.path.exists(os.path.join(DATASET_DIR, split)):
            print(f"Downloading {split} set from HuggingFace benchmark mirror...")
            urllib.request.urlretrieve(url, zip_path)
            print(f"Extracting {split} set...")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(DATASET_DIR)
            if os.path.exists(zip_path):
                os.remove(zip_path)
            print(f"Unpacked {split} set.")
        else:
            print(f"{split} partition already exists at {os.path.join(DATASET_DIR, split)}")

    print(f"Secondary dataset ready at: {DATASET_DIR}")


if __name__ == "__main__":
    download_and_extract()
