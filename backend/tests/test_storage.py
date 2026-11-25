import pytest
from pathlib import Path
from app.services.storage import LocalStorageBackend, get_storage, StorageBackend


def test_local_storage_crud(tmp_path):
    storage = LocalStorageBackend(base_dir=tmp_path)

    # 1. Save
    rel_path = "inspections/10/photo.jpg"
    data = b"image_raw_bytes_test"
    stored_path = storage.save(rel_path, data)
    assert stored_path == "inspections/10/photo.jpg"

    # 2. Exists
    assert storage.exists(rel_path) is True
    assert storage.exists("non_existent.jpg") is False

    # 3. Get
    retrieved = storage.get(rel_path)
    assert retrieved == data
    assert storage.get("non_existent.jpg") is None

    # 4. Local path
    local_p = storage.get_local_path(rel_path)
    assert local_p is not None
    assert local_p.exists()

    # 5. URL
    url = storage.get_url(rel_path)
    assert url == "/storage/inspections/10/photo.jpg"

    # 6. Delete
    assert storage.delete(rel_path) is True
    assert storage.exists(rel_path) is False
    assert storage.delete(rel_path) is False


def test_path_traversal_prevention(tmp_path):
    storage = LocalStorageBackend(base_dir=tmp_path)

    # Attempt directory traversal
    with pytest.raises(ValueError, match="Path traversal detected"):
        storage.save("../../etc/passwd", b"malicious")


def test_get_storage_factory():
    storage = get_storage()
    assert isinstance(storage, StorageBackend)
