"""Pytest test configuration and async database fixtures."""

import pytest
import pytest_asyncio
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database import Base
from core.config import settings
from models import Chat, User, Warn, AuditLog

# Always ensure a test superadmin is configured for the entire test suite
settings.SUPERADMIN_IDS = "8667615215,123456789"

# In-memory SQLite for blazing fast isolated testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"



@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated, clean in-memory database session for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
