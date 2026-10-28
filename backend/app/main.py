"""Main application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.dependencies import get_engine, get_session_maker, get_settings
from app.middleware.request_id import RequestIDMiddleware
from app.models.base import Base
from app.routers.auth import limiter
from app.routers.auth import router as auth_router

settings = get_settings()
engine = get_engine(settings)
async_session_maker = get_session_maker(settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown hooks."""
    # On startup: create all tables for dev database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # On shutdown: dispose the async database engine
    await engine.dispose()


app = FastAPI(
    title="Lavanya Learning System API",
    version="0.1.0",
    lifespan=lifespan,
)

# Slowapi rate limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middlewares
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/v1/health", tags=["system"])
async def api_health_check() -> dict[str, str]:
    """API versioned health check endpoint."""
    return {"status": "ok"}
