from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.core.database as db_module
from app.core.config import settings
from app.core.storage import InMemoryStorageBackend, set_storage_backend
from app.main import app

# Test database engine configured with NullPool to prevent event loop connection reuse conflicts
test_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_environment(monkeypatch):
    """Sets up clean test isolation: in-memory storage, NullPool DB sessions, and mocked broker."""
    # 1. In-memory storage backend
    mock_storage = InMemoryStorageBackend()
    set_storage_backend(mock_storage)

    # 2. Database session override
    monkeypatch.setattr(db_module, "AsyncSessionLocal", TestAsyncSessionLocal)
    monkeypatch.setattr(db_module, "engine", test_engine)

    # 3. Disable rate limiting by default in unit/integration test suite
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestAsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[db_module.get_db_session] = override_get_db_session

    yield mock_storage

    app.dependency_overrides.pop(db_module.get_db_session, None)


@pytest.fixture(autouse=True)
def mock_celery_task_delay():
    """Mock Celery delay in unit tests to prevent blocking when Redis is not running."""
    with patch("app.workers.tasks.test_job_task.delay") as mock_delay_test, \
         patch("app.workers.tasks.process_job_task.delay"):
        yield mock_delay_test


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provides an asynchronous test client for the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an async database session with NullPool for test assertions."""
    async with TestAsyncSessionLocal() as session:
        yield session
