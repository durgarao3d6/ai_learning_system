# Lavanya Learning System — Backend (Phase 1)

FastAPI-powered backend for the Proctored RAG Quiz System.

## Architecture Highlights

- **Framework**: FastAPI with `/api/v1/` route prefixing
- **Database & ORM**: SQLAlchemy 2.x async ORM with Alembic migrations and SQLite (`aiosqlite`)
- **Authentication**: Argon2 password hashing + JWT tokens (HS256, 15m access token, 7d refresh token)
- **Configuration**: Pydantic v2 `BaseSettings` reading from `.env`
- **Rate Limiting**: slowapi on sensitive endpoints (e.g. login)
- **AI & Embedding Provider Abstraction**: `LLMProvider` and `EmbeddingProvider` protocols decouples business logic from vendor SDKs (Ollama for dev, OpenAI stubbed for Phase 2)
- **Observability**: `RequestIDMiddleware` ensuring `X-Request-ID` tracing on every request with structured JSON logging

## Setup Instructions

### 1. Environment & Dependencies

Create and activate a virtual environment (Python 3.11+):

```bash
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -e ".[dev]"
```

### 2. Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Run Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive OpenAPI docs will be available at: `http://localhost:8000/docs`

### 5. Run Automated Tests

```bash
pytest
```
