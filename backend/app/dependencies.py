"""FastAPI dependency injection providers."""

import uuid
from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings
from app.models.user import User
from app.services.auth_service import decode_token
from app.services.providers.base import EmbeddingProvider, LLMProvider
from app.services.providers.ollama_provider import OllamaLLMProvider
from app.services.providers.openai_provider import OpenAILLMProvider
from app.services.providers.sentence_transformer_provider import (
    SentenceTransformerEmbeddingProvider,
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)

_engines: dict[str, AsyncEngine] = {}
_session_makers: dict[str, async_sessionmaker[AsyncSession]] = {}


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Get or create the AsyncEngine for the configured database URL."""
    if settings is None:
        settings = get_settings()
    if settings.DATABASE_URL not in _engines:
        _engines[settings.DATABASE_URL] = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True,
        )
    return _engines[settings.DATABASE_URL]


def get_session_maker(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """Get or create the async sessionmaker for the database."""
    if settings is None:
        settings = get_settings()
    if settings.DATABASE_URL not in _session_makers:
        engine = get_engine(settings)
        _session_makers[settings.DATABASE_URL] = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_makers[settings.DATABASE_URL]


async def get_db(settings: Settings = Depends(get_settings)) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session."""
    session_maker = get_session_maker(settings)
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


def get_llm_provider(settings: Settings = Depends(get_settings)) -> LLMProvider:
    """Factory returning configured LLMProvider implementation."""
    match settings.LLM_PROVIDER.lower():
        case "ollama":
            return OllamaLLMProvider(settings=settings)
        case "openai":
            return OpenAILLMProvider(settings=settings)
        case _:
            raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")


def get_embedding_provider(settings: Settings = Depends(get_settings)) -> EmbeddingProvider:
    """Factory returning configured EmbeddingProvider implementation."""
    match settings.EMBEDDING_PROVIDER.lower():
        case "sentence_transformer":
            return SentenceTransformerEmbeddingProvider(settings=settings)
        case _:
            raise ValueError(f"Unknown embedding provider: {settings.EMBEDDING_PROVIDER}")


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Authenticate and return the current active User from JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token, settings)
    user_id_str = payload.get("sub")
    token_type = payload.get("type")

    if not user_id_str or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
