"""
Database session management and connection pooling using SQLAlchemy 2.x async engine.
Provides FastAPI dependency injection and standalone context manager for background workers.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# Initialize Async Engine with connection pooling settings
engine: AsyncEngine = create_async_engine(
    get_settings().DATABASE_URL,
    echo=get_settings().DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Test connection viability before handing out from pool
)

# Factory for creating async sessions
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an independent AsyncSession per request.
    Ensures sessions are closed properly when the request finishes.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_standalone_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Standalone context manager for background tasks, CLI scripts, and Celery workers.
    Usage:
        async with get_standalone_db_session() as session:
            ...
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
