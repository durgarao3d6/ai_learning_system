# Database Choices — SQLite for Dev, PostgreSQL for Prod with SQLAlchemy and Alembic

## What it is
We use SQLite (`sqlite+aiosqlite`) for local development and testing, and PostgreSQL (`postgresql+asyncpg`) for production, unified under SQLAlchemy 2.0's asynchronous ORM. Schema migrations are managed as code from day one using Alembic. This setup enables instantaneous developer onboarding with zero database infrastructure while ensuring seamless, automated schema deployment to production with a single configuration switch.

## Why we need it / Why this approach
Local development should have near-zero friction. Requiring a running PostgreSQL daemon or Docker container just to run a test or test an endpoint stops new contributors in their tracks. SQLite is a zero-configuration, serverless, file-backed database engine: a developer can clone the repository, run the application, and start coding within seconds.

However, SQLite is not suitable for high-concurrency production deployments with concurrent writes. To bridge dev and prod without rewriting queries:
1. **SQLAlchemy 2.0 Async ORM**: By coding against SQLAlchemy models and using async sessions, the application code remains completely agnostic of the underlying database engine. Switching from local SQLite to production PostgreSQL requires changing only the `DATABASE_URL` environment variable—zero business logic or data access code is altered.
2. **Alembic from day one**: Schema changes must be auditable and reproducible. Even during Phase 1 with SQLite, all table definitions are managed through version-controlled migration scripts. When we deploy to PostgreSQL in staging or production, running `alembic upgrade head` creates the complete, exact schema. Without Alembic from the start, moving to PostgreSQL requires manually exporting schemas, fixing dialect incompatibilities, or relying on `Base.metadata.create_all()`, which cannot handle incremental schema evolution.
3. **Why not raw SQL**: Writing raw SQL strings forfeits Python type hints, IDE auto-completion, and compile-time validation. Refactoring a column name would require error-prone grep-and-replace across query strings. Raw SQL also exposes the codebase to subtle dialect discrepancies between SQLite and PostgreSQL syntax.
4. **Why not PostgreSQL from day one**: Enforcing PostgreSQL locally forces every contributor to install, configure, and maintain a local database service or run Docker Desktop continuously, consuming substantial system resources and complicating automated CI test runs.

## Alternatives considered
| Option | Why rejected |
|---|---|
| PostgreSQL from day one | Requires Docker Desktop or a running local Postgres daemon for every contributor. Adds friction to onboarding, complicates initial CI pipelines, and slows down local test execution. |
| Raw SQL (asyncpg / aiosqlite directly) | No compile-time type safety. Queries break across dialects (e.g., parameter binding `%s` vs `?`), column refactoring requires searching strings, and manual result mapping creates boilerplate. |
| Tortoise ORM or Peewee | Smaller ecosystem and community support compared to SQLAlchemy. Alembic provides far more robust autogeneration, branch merging, and production battle-testing than alternative migration tools. |
| No migrations (`Base.metadata.create_all()`) | Cannot handle incremental schema updates without dropping existing tables and losing data. Completely unviable for production upgrades. |

## Implementation details

The database connection is configured in `backend/app/config.py` using Pydantic Settings. The engine and session factory are created in `backend/app/models/base.py` (or `backend/app/database.py`).

### 1. Connection URL Pattern
The application switches drivers based on the `DATABASE_URL` variable:

```bash
# Local Development (.env)
DATABASE_URL=sqlite+aiosqlite:///./dev.db

# Production (.env.production)
DATABASE_URL=postgresql+asyncpg://quiz_user:quiz_secure_pass@db.internal:5432/proctored_quiz_prod
```

### 2. Async Engine and Session Setup
```python
# backend/app/models/base.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

# SQLite requires connect_args to allow multithreaded async access
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass
```

### 3. Alembic Async Configuration
Alembic is configured in `migrations/env.py` to inspect `Base.metadata` and execute migrations asynchronously using `async_engine`:

```python
# migrations/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from alembic import context

from app.models.base import Base
import app.models  # Ensures all ORM models are registered on Base.metadata
from app.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_settings().DATABASE_URL
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    # Offline migration handling
    pass
else:
    run_migrations_online()
```

## Tradeoffs and known limitations
1. **SQLite concurrency constraints**: SQLite locks the database file on writes (`database is locked` error under high concurrent writes). While acceptable for single-developer local workflows, integration tests simulating dozens of concurrent quiz submissions must configure connection pool timeouts or run against a Postgres test container.
2. **Dialect discrepancies**: SQLite does not natively enforce enum types, foreign key constraints (unless explicitly enabled with `PRAGMA foreign_keys = ON`), or full `ALTER TABLE` operations without batch mode (`render_as_batch=True` must be enabled in Alembic).
3. **Advanced types**: PostgreSQL features such as native JSONB operators and array columns require generic SQLAlchemy types (e.g., `JSON`) to ensure compatibility with SQLite during local testing.
4. **CI verification required**: Because developers write against SQLite locally, CI pipelines must run a secondary test suite against an actual PostgreSQL service container to catch any dialect-specific regressions before merging to `main`.
