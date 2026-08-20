"""Async SQLAlchemy 2.0 Database configuration and session management."""

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from core.config import settings
from core.logger import logger


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""
    pass


# Global engine and sessionmaker instances
engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=(settings.LOG_LEVEL.upper() == "DEBUG"),
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injector yielding an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as err:
            await session.rollback()
            logger.error(f"Database session error: {err}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    logger.info("Initializing database connection and tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully.")


async def close_db() -> None:
    """Close database engine and active connections."""
    logger.info("Closing database engine...")
    await engine.dispose()
    logger.info("Database engine closed.")
