import abc
import io
import logging
from pathlib import Path
from typing import Optional, Union

from app.config import settings

logger = logging.getLogger("infrascan.storage")


class StorageBackend(abc.ABC):
    """
    Abstract storage backend interface for file uploads, masks, processed images, and reports.
    """

    @abc.abstractmethod
    def save(self, relative_path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Store data at the given relative path and return the stored identifier / relative key.
        """
        pass

    @abc.abstractmethod
    def get(self, relative_path: str) -> Optional[bytes]:
        """
        Retrieve binary data from storage. Returns None if key does not exist.
        """
        pass

    @abc.abstractmethod
    def delete(self, relative_path: str) -> bool:
        """
        Delete the file from storage. Returns True if deleted, False if not found.
        """
        pass

    @abc.abstractmethod
    def exists(self, relative_path: str) -> bool:
        """
        Check if a file exists at the given relative path.
        """
        pass

    @abc.abstractmethod
    def get_url(self, relative_path: str) -> str:
        """
        Return a publicly accessible URL or API download URL for the file.
        """
        pass

    @abc.abstractmethod
    def get_local_path(self, relative_path: str) -> Optional[Path]:
        """
        Return the local Path on the filesystem if available, or None if remote-only.
        """
        pass


class LocalStorageBackend(StorageBackend):
    """
    Local filesystem storage provider with path traversal sanitization.
    """

    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        self.base_dir = Path(base_dir).resolve() if base_dir else settings.storage_path.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        clean_rel = Path(relative_path).as_posix().lstrip("/\\")
        # Prevent directory traversal
        target = (self.base_dir / clean_rel).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return target

    def save(self, relative_path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        target = self._resolve_safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        # Return normalized posix relative path
        return target.relative_to(self.base_dir).as_posix()

    def get(self, relative_path: str) -> Optional[bytes]:
        try:
            target = self._resolve_safe_path(relative_path)
            if target.exists() and target.is_file():
                return target.read_bytes()
            return None
        except Exception as e:
            logger.warning(f"Failed to read file {relative_path}: {e}")
            return None

    def delete(self, relative_path: str) -> bool:
        try:
            target = self._resolve_safe_path(relative_path)
            if target.exists() and target.is_file():
                target.unlink()
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to delete file {relative_path}: {e}")
            return False

    def exists(self, relative_path: str) -> bool:
        try:
            target = self._resolve_safe_path(relative_path)
            return target.exists() and target.is_file()
        except Exception:
            return False

    def get_url(self, relative_path: str) -> str:
        clean_rel = Path(relative_path).as_posix().lstrip("/\\")
        return f"/storage/{clean_rel}"

    def get_local_path(self, relative_path: str) -> Optional[Path]:
        try:
            return self._resolve_safe_path(relative_path)
        except Exception:
            return None


class S3StorageBackend(StorageBackend):
    """
    AWS S3 and MinIO compatible object storage backend.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
    ):
        self.bucket_name = bucket_name or settings.S3_BUCKET
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key = access_key or settings.S3_ACCESS_KEY
        self.secret_key = secret_key or settings.S3_SECRET_KEY
        self.region = region or settings.S3_REGION
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import boto3
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
            return self._client
        except ImportError:
            raise RuntimeError("boto3 is required for S3StorageBackend. Run `pip install boto3`.")

    def save(self, relative_path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        client = self._get_client()
        clean_key = Path(relative_path).as_posix().lstrip("/\\")
        client.put_object(
            Bucket=self.bucket_name,
            Key=clean_key,
            Body=data,
            ContentType=content_type,
        )
        return clean_key

    def get(self, relative_path: str) -> Optional[bytes]:
        client = self._get_client()
        clean_key = Path(relative_path).as_posix().lstrip("/\\")
        try:
            resp = client.get_object(Bucket=self.bucket_name, Key=clean_key)
            return resp["Body"].read()
        except Exception as e:
            logger.warning(f"S3 get failed for {clean_key}: {e}")
            return None

    def delete(self, relative_path: str) -> bool:
        client = self._get_client()
        clean_key = Path(relative_path).as_posix().lstrip("/\\")
        try:
            client.delete_object(Bucket=self.bucket_name, Key=clean_key)
            return True
        except Exception as e:
            logger.warning(f"S3 delete failed for {clean_key}: {e}")
            return False

    def exists(self, relative_path: str) -> bool:
        client = self._get_client()
        clean_key = Path(relative_path).as_posix().lstrip("/\\")
        try:
            client.head_object(Bucket=self.bucket_name, Key=clean_key)
            return True
        except Exception:
            return False

    def get_url(self, relative_path: str) -> str:
        clean_key = Path(relative_path).as_posix().lstrip("/\\")
        if self.endpoint_url:
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{clean_key}"
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{clean_key}"

    def get_local_path(self, relative_path: str) -> Optional[Path]:
        return None


# Global storage singleton
_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """
    Get the configured storage backend singleton (Local or S3/MinIO).
    """
    global _storage_instance
    if _storage_instance is None:
        if settings.STORAGE_BACKEND.lower() == "s3":
            _storage_instance = S3StorageBackend()
        else:
            _storage_instance = LocalStorageBackend()
    return _storage_instance
