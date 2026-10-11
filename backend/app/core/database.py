import asyncio
from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text
from sqlalchemy.orm import declarative_base

from app.core.config import settings
from app.core.logging import logger

Base = declarative_base()

# Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to provide an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_health() -> Dict[str, Any]:
    """Checks PostgreSQL connectivity and returns a status dictionary."""
    try:
        async with asyncio.timeout(3.0):
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT 1"))
                row = result.scalar()
                if row == 1:
                    return {"status": "connected"}
                return {"status": "error", "error": "Unexpected return value from DB"}
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return {"status": "disconnected", "error": str(e)}
