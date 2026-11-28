import io
import uuid
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException, status
from app.core.config import settings
from app.storage.base import StorageBackend

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.STORAGE_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_resolve(self, relative_path: str) -> Path:
        target = (self.base_dir / relative_path).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path")
        return target

    def save_file(self, content: bytes, subdir: str, filename: str) -> str:
        ext = Path(filename).suffix.lower() or ".bin"
        stored_name = f"{uuid.uuid4().hex}{ext}"
        rel_key = f"{subdir}/{stored_name}"
        target = self._safe_resolve(rel_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return rel_key

    def get_file_path(self, storage_key: str) -> Path:
        target = self._safe_resolve(storage_key)
        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")
        return target

    def delete_file(self, storage_key: str) -> None:
        target = self._safe_resolve(storage_key)
        if target.exists():
            target.unlink()


def validate_image_bytes(content: bytes, mime_type: str) -> tuple[int, int]:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image format")
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
        with Image.open(io.BytesIO(content)) as img:
            return img.size
    except (UnidentifiedImageError, Exception) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Corrupted or unreadable image file") from exc

