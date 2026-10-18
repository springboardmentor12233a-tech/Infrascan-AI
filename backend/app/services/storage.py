import os
import shutil
from typing import BinaryIO


class LocalStorage:
    """Local disk storage abstraction that can be swapped with S3 / MinIO."""
    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_file(self, filename: str, file_obj: BinaryIO) -> str:
        dest_path = os.path.join(self.base_dir, filename)
        file_obj.seek(0)
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)
        return dest_path

    def get_file_path(self, filename: str) -> str:
        return os.path.join(self.base_dir, filename)

    def file_exists(self, filename: str) -> bool:
        return os.path.exists(os.path.join(self.base_dir, filename))

    def delete_file(self, filename: str) -> bool:
        path = os.path.join(self.base_dir, filename)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


storage = LocalStorage()
