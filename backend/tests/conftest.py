"""Pytest fixtures for backend integration and unit tests."""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings
from app.dependencies import get_db, get_settings
from app.main import app
from app.models.base import Base
from app.routers.auth import limiter

TEST_DB_FILE = "./test.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
TEST_SECRET_KEY = "test-secret-key-32-chars-long-for-jwt"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provide settings configured for testing."""
    return Settings(
        DATABASE_URL=TEST_DATABASE_URL,
        SECRET_KEY=TEST_SECRET_KEY,
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        LLM_PROVIDER="ollama",
        EMBEDDING_PROVIDER="sentence_transformer",
    )


@pytest.fixture(scope="session")
def test_engine(test_settings: Settings) -> AsyncEngine:
    """Create a persistent test engine for the test session."""
    return create_async_engine(test_settings.DATABASE_URL, echo=False)


@pytest.fixture(scope="session")
def test_session_maker(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a sessionmaker bound to the test engine."""
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_test_db(test_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def async_client(
    test_settings: Settings,
    test_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient for FastAPI testing with dependency overrides."""
    async def override_get_settings() -> Settings:
        return test_settings

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()

    # Reset limiter storage to avoid rate limit leak between test runs
    if hasattr(limiter, "_storage") and hasattr(limiter._storage, "reset"):
        limiter._storage.reset()

    app.dependency_overrides[get_settings] = override_get_settings
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db_file():
    """Remove SQLite test database file after test suite finishes."""
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass
