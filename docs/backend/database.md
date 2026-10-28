# Database Layer — Async Sessions, DeclarativeBase, TimestampMixin, and Alembic

## What it is
The persistence layer is built on SQLAlchemy 2.0 Async (`sqlalchemy.ext.asyncio`). It uses a strict per-request session lifecycle via FastAPI's `yield` dependency, a unified `DeclarativeBase` paired with a reusable `TimestampMixin` for audit trails, and an automated Alembic migration workflow that treats all schema alterations as version-controlled code.

## Why we need it / Why this approach
Database session management and schema evolutions are frequent sources of production bugs, data corruption, and deadlocks if not strictly standardized:
1. **Async session lifecycle per request**: Synchronous database drivers block the Python asyncio event loop, collapsing server throughput under concurrent I/O. Using `AsyncSession` ensures non-blocking query execution. Providing the session via a FastAPI `yield` dependency (`get_db`) guarantees that every HTTP request operates within its own isolated transaction boundary and that the database connection is guaranteed to close—even if an unhandled exception or early return occurs.
2. **Explicit transaction boundaries**: Implicit commits hide bugs and risk partial writes. Every write operation must either use `async with session.begin():` (which commits on exit and rolls back on exception) or an explicit `await session.commit()`.
3. **Auditing standardization via `TimestampMixin`**: Almost every entity (users, quizzes, attempts, proctor logs) requires timestamps for creation and modification. Manually adding `created_at` and `updated_at` columns to every table invites discrepancies in column names, timezones, and nullability. A shared `TimestampMixin` uses database-level defaults (`server_default=func.now()`), guaranteeing accurate UTC timestamps regardless of application clock drift.
4. **Zero manual schema mutations**: Modifying production schemas manually via SQL shells (e.g. `ALTER TABLE`) is catastrophic for maintainability: changes cannot be rolled back safely, staging and production drift apart, and other developers cannot replicate the state. Alembic makes schema evolution reproducible and testable.

## Alternatives considered
| Option | Why rejected |
|---|---|
| Synchronous SQLAlchemy sessions (`SessionLocal`) | Blocks the async event loop during every database query, destroying FastAPI's concurrency and throughput. |
| Global session instance | Causes race conditions, transaction collisions across concurrent requests, and severe connection pool exhaustion. |
| Automatic table creation via `Base.metadata.create_all()` | Destructive or ineffective when altering existing tables; cannot migrate data, add non-nullable columns to existing tables, or execute down-revisions. |
| Manual SQL migration scripts | Prone to human syntax errors, requires manual tracking of applied versions, and lacks automatic diffing against ORM model declarations. |

## Implementation details

### 1. Base Model and TimestampMixin (`backend/app/models/base.py`)
```python
# backend/app/models/base.py
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs, DeclarativeBase):
    """Declarative root class for all ORM models."""
    pass

class TimestampMixin:
    """
    Standard audit mixin adding created_at and updated_at with UTC server defaults.
    Ensures all models record consistent, database-generated timestamps.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

### 2. Concrete Model Example (`backend/app/models/user.py`)
All domain models inherit from both `Base` and `TimestampMixin`:

```python
# backend/app/models/user.py
import uuid
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="student", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

### 3. Session Dependency with Automatic Cleanup (`backend/app/dependencies.py`)
FastAPI's generator dependency (`yield`) guarantees execution of the `finally` block after the HTTP response has been transmitted to the client:

```python
# backend/app/dependencies.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session per request.
    Rolls back uncommitted transactions on exception and guarantees session closure.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 4. Alembic Discovery and Migration Workflow
Alembic must discover all ORM models to detect schema differences. In `migrations/env.py`, we import `Base` and all model modules:

```python
# migrations/env.py
from app.models.base import Base
# Import all model modules so that their tables are registered on Base.metadata
import app.models.user
import app.models.quiz
import app.models.attempt
import app.models.proctor

target_metadata = Base.metadata
```

#### The Migration Workflow:
1. **Modify ORM models**: Edit or add Python classes in `backend/app/models/`.
2. **Generate migration script**:
   ```bash
   alembic revision --autogenerate -m "create users and quizzes tables"
   ```
3. **Review generated script**: Inspect the created file under `migrations/versions/xxxx_create_users_and_quizzes_tables.py` to confirm table names, column constraints, and foreign keys.
4. **Apply migration**:
   ```bash
   alembic upgrade head
   ```
5. **Rollback (if needed)**:
   ```bash
   alembic downgrade -1
   ```

## Tradeoffs and known limitations
1. **Lazy loading limitations with async**: In synchronous SQLAlchemy, accessing an unloaded relationship (e.g., `quiz.questions`) triggers a synchronous lazy-load query behind the scenes. In async SQLAlchemy, this raises `sqlalchemy.exc.MissingGreenlet`. All relationships must be eagerly loaded using `selectinload()` or `joinedload()`.
2. **SQLite ALTER TABLE limitations**: SQLite has limited native support for `ALTER TABLE` operations (e.g., modifying column nullability or dropping columns). Alembic must be configured with `render_as_batch=True` in `migrations/env.py` when targeting SQLite so it can recreate tables under the hood during migrations.
3. **Explicit commit discipline**: Forgetting `await session.commit()` before an endpoint returns will result in discarded data without raising an error because the session context exits without committing. Developers must write integration tests verifying database persistence.
