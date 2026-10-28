# Backend Project Structure — Layered Architecture and Separation of Concerns

## What it is
The backend is structured into clear, decoupled layers where each folder has a single, strictly enforced responsibility: routing, business logic, data models, schema serialization, vendor adapters, and configuration. Cross-layer leakage—such as putting database queries or business rules inside route handlers, or mixing database entities with API response schemas—is strictly prohibited.

## Why we need it / Why this approach
Without structural guardrails, FastAPI applications degenerate into monolithic route handlers where database sessions, serialization logic, business validations, and external API requests are entangled in single 500-line functions.
1. **Thin routers**: Routers exist only to parse HTTP requests, trigger Pydantic schema validation, delegate work to an injected service, and return an HTTP response. Routers contain zero business calculations, zero SQL queries, and zero direct calls to vendor SDKs. This allows the API protocol layer to change without affecting domain logic.
2. **Pure, testable services**: The `services/` layer houses all domain rules (e.g., computing proctoring risk scores, grading quizzes, scheduling LLM generation). Services take plain Python arguments or Pydantic models and return domain objects. They can be unit-tested without launching an HTTP test client, setting up ASGI headers, or mocking network sockets.
3. **Strict separation of ORM models and Pydantic schemas**:
   - `models/` (SQLAlchemy ORM) define database tables, foreign keys, relationships, and persistence indexes. They must never contain business methods or HTTP formatting logic.
   - `schemas/` (Pydantic) define strict data contracts for incoming requests and outgoing responses.
   - **Why separate them**: An ORM model maps directly to internal database state, including sensitive columns like `password_hash`, internal encryption nonces, foreign keys, and audit timestamps. Returning an ORM model directly from an endpoint risks catastrophic data leaks. Pydantic schemas explicitly whitelist exactly what the client is permitted to view. Schemas also handle validation (e.g., regex checks, email formatting, string trimming) before data reaches the persistence tier.
4. **Isolated vendor adapters (`services/providers/`)**: AI vendors (Ollama, OpenAI, Anthropic, HuggingFace) update their SDKs frequently. Isolating each vendor into its own single-class file under `services/providers/` ensures that vendor-specific quirks, prompt formatting tricks, or error handling never pollute domain services. Unit tests simply substitute a lightweight fake provider.

## Alternatives considered
| Option | Why rejected |
|---|---|
| Monolithic "all-in-one" router files (queries & logic in route functions) | Untestable without spinning up the full HTTP server; massive code duplication; high probability of leaking sensitive DB fields in API responses. |
| Single model layer (SQLModel combining ORM and Pydantic into one class) | Conflates database schema definitions with API request/response contracts. In practice, API inputs and DB entities diverge rapidly (e.g., omit `password_hash` on output, omit auto-generated `id` on creation). Causes leaky abstractions. |
| Django-style fat models (business logic attached to ORM entities) | Tightly couples business logic to the database lifecycle and active sessions, making async testing and pure unit testing tedious and slow. |
| Feature-based vertical slicing (e.g., `modules/auth/{models,views,services}`) | Adds excessive directory nesting for small-to-medium teams and complicates cross-domain queries and Alembic migration discovery during early phases. |

## Implementation details

### 1. Directory Tree Layout
```
backend/
  app/
    main.py          # Application entry point, middleware wiring, exception handlers
    config.py        # Centralized Pydantic BaseSettings environment configuration
    dependencies.py  # FastAPI Depends factories (get_db, get_current_user, providers)
    models/          # SQLAlchemy ORM models (table structures and DB relationships)
      base.py        # Base DeclarativeBase and TimestampMixin
      user.py        # User and Role tables
      quiz.py        # Quiz, Question, and Option tables
      attempt.py     # Exam attempt and submission tables
      proctor.py     # Proctor event and violation log tables
    schemas/         # Pydantic request and response models
      auth.py        # LoginRequest, TokenResponse, UserResponse
      quiz.py        # QuizCreate, QuizDetailResponse, QuestionResponse
      attempt.py     # AttemptStartRequest, SubmitAnswerRequest
      proctor.py     # ViolationEventCreate, ProctorSummaryResponse
    routers/         # Thin FastAPI route handlers (HTTP parsing & response formatting)
      api_v1.py      # Combines all domain routers with /api/v1 prefix
      auth.py        # /api/v1/auth/*
      quizzes.py     # /api/v1/quizzes/*
      documents.py   # /api/v1/documents/*
      attempts.py    # /api/v1/attempts/*
      proctor.py     # /api/v1/proctor/*
    services/        # Pure domain business logic (no HTTP dependencies)
      auth_service.py      # Password verification, JWT generation, user lookup
      quiz_service.py      # Quiz creation, question validation, state management
      rag_service.py       # Chunking, vector retrieval, prompt orchestration
      proctor_service.py   # Sliding-window violation aggregation and scoring
      providers/           # LLM and Embedding vendor integrations
        base.py                           # Protocol definitions (LLMProvider, EmbeddingProvider)
        ollama_provider.py                # Ollama integration
        openai_provider.py                # OpenAI integration
        sentence_transformer_provider.py  # Local sentence-transformers integration
        openai_embedding_provider.py      # OpenAI text-embedding integration
    middleware/      # ASGI middleware (CORS, Request-ID logging, rate-limit headers)
  migrations/        # Alembic schema migration scripts
    versions/        # Individual migration files
    env.py           # Alembic runtime environment
  tests/             # Pytest suite
    conftest.py      # Test fixtures (async DB session, test client, fake providers)
    unit/            # Unit tests for pure services and providers
    integration/     # API integration tests using AsyncClient
```

### 2. Code Example: Thin Router vs Business Service

#### The Thin Router (`backend/app/routers/quizzes.py`)
```python
# backend/app/routers/quizzes.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.schemas.quiz import QuizCreateRequest, QuizResponse
from app.schemas.user import UserResponse
from app.services.quiz_service import QuizService

router = APIRouter()

@router.post("/", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    payload: QuizCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Thin router: validates input via Pydantic, calls service, returns serialized response
    service = QuizService(db)
    quiz = await service.create_quiz_for_user(user_id=current_user.id, data=payload)
    return quiz
```

#### The Pure Business Service (`backend/app/services/quiz_service.py`)
```python
# backend/app/services/quiz_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.quiz import Quiz
from app.schemas.quiz import QuizCreateRequest

class QuizService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_quiz_for_user(self, user_id: str, data: QuizCreateRequest) -> Quiz:
        # Business logic: validate business rules, persist, and return entity
        quiz = Quiz(
            title=data.title,
            creator_id=user_id,
            time_limit_minutes=data.time_limit_minutes,
            proctoring_enabled=data.proctoring_enabled,
        )
        self.db.add(quiz)
        await self.db.commit()
        await self.db.refresh(quiz)
        return quiz
```

## Tradeoffs and known limitations
1. **Initial file boilerplate**: Simple CRUD features require touching multiple files (`models/`, `schemas/`, `routers/`, `services/`). For trivial read operations, this feels repetitive compared to directly returning an ORM query in a route handler, but it pays immediate dividends as soon as business validation or security rules expand.
2. **Object mapping overhead**: Converting between SQLAlchemy models and Pydantic schemas incurs a minor CPU serialization cost. In Python, this is measured in sub-milliseconds and is completely dwarfed by database I/O and LLM network latency.
3. **Discipline required**: Developers must resist the temptation to "quickly" execute a `db.execute()` query directly inside a router function. Code review checklists must verify that routers remain thin.
