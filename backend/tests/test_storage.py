import pytest
from app.core.storage import InMemoryStorageBackend, StorageError


@pytest.mark.asyncio
async def test_in_memory_storage_upload_download():
    storage = InMemoryStorageBackend()
    key = "inputs/2026/10/09/job1/file1.pdf"
    content = b"%PDF-1.4 test data"

    # Upload
    uploaded_key = await storage.upload(key, content, content_type="application/pdf")
    assert uploaded_key == key

    # Exists
    assert await storage.exists(key) is True
    assert await storage.exists("non-existent-key") is False

    # Download
    downloaded = await storage.download(key)
    assert downloaded == content

    # Metadata
    meta = await storage.get_metadata(key)
    assert meta["size_bytes"] == len(content)
    assert meta["content_type"] == "application/pdf"

    # Presigned URLs
    up_url = await storage.generate_presigned_upload_url(key)
    assert "upload_expires=900" in up_url

    down_url = await storage.generate_presigned_download_url(
        key, filename="custom_name.pdf"
    )
    assert "download_expires=300" in down_url
    assert "filename=custom_name.pdf" in down_url

    # Health check
    health = await storage.check_health()
    assert health["status"] == "connected"

    # Delete
    await storage.delete(key)
    assert await storage.exists(key) is False

    with pytest.raises(StorageError):
        await storage.download(key)


@pytest.mark.asyncio
async def test_in_memory_storage_delete_many():
    storage = InMemoryStorageBackend()
    keys = ["k1", "k2", "k3"]
    for k in keys:
        await storage.upload(k, b"data")

    assert await storage.exists("k1") is True
    assert await storage.exists("k2") is True
    assert await storage.exists("k3") is True

    await storage.delete_many(["k1", "k3"])
    assert await storage.exists("k1") is False
    assert await storage.exists("k2") is True
    assert await storage.exists("k3") is False
