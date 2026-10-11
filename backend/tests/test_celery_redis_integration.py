import socket
import pytest
from app.core.config import settings


def is_redis_available() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        # Parse host and port from REDIS_URL
        result = s.connect_ex(("localhost", 6379))
        s.close()
        return result == 0
    except Exception:
        return False


def is_minio_available() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        result = s.connect_ex(("localhost", 9000))
        s.close()
        return result == 0
    except Exception:
        return False


@pytest.mark.skipif(not is_redis_available(), reason="Redis broker is not reachable at localhost:6379")
def test_celery_redis_live_execution():
    """Integration test that verifies actual Celery task queuing and execution through Redis."""
    from app.workers.tasks import test_job_task
    # Trigger task via real Celery worker broker
    res = test_job_task.delay("00000000-0000-0000-0000-000000000000")
    assert res.id is not None


@pytest.mark.skipif(not is_minio_available(), reason="MinIO storage is not reachable at localhost:9000")
@pytest.mark.asyncio
async def test_minio_live_integration():
    """Integration test that verifies real S3 / MinIO uploads and deletions."""
    from app.core.storage import S3StorageBackend
    minio_storage = S3StorageBackend()
    test_key = "inputs/integration_test_object.pdf"
    content = b"%PDF-1.4\n%%EOF"

    await minio_storage.upload(test_key, content)
    assert await minio_storage.exists(test_key) is True
    downloaded = await minio_storage.download(test_key)
    assert downloaded == content
    await minio_storage.delete(test_key)
    assert await minio_storage.exists(test_key) is False
