from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    @abstractmethod
    def save_file(self, content: bytes, subdir: str, filename: str) -> str:
        """Save bytes and return relative storage key."""

    @abstractmethod
    def get_file_path(self, storage_key: str) -> Path:
        """Resolve safe local path for a storage key."""

    @abstractmethod
    def delete_file(self, storage_key: str) -> None:
        """Delete file if it exists."""

