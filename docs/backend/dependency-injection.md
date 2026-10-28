# Dependency Injection — FastAPI `Depends`, Provider Factories, and Test Overrides

## What it is
We use FastAPI's built-in `Depends` mechanism for managing object lifecycles, configuration injection, database sessions, authentication context, and external vendor providers. Dependencies are declared hierarchically and resolved per-request. Global singletons and module-level instantiations are explicitly prohibited.

## Why we need it / Why this approach
In Python applications, it is common to create module-level global objects (e.g. `db = Database()`, `llm = OpenAIClient()`). While easy to write initially, this design severely harms testability, concurrency, and modularity:
1. **Composable hierarchical resolution**: Real-world operations require nested dependencies. For example, obtaining the currently authenticated user (`get_current_user`) requires reading JWT secrets from application settings (`get_settings`) and querying the database (`get_db`). FastAPI's dependency injection automatically inspects parameter signatures, builds a Directed Acyclic Graph (DAG) of dependencies, executes them in topological order, and ensures cleanup blocks (like closing database sessions) execute after the response is sent.
2. **Provider abstraction via factories**: Routes and domain services that need an LLM or embedding model never instantiate concrete vendor classes. Instead, they depend on provider factories (`get_llm_provider`, `get_embedding_provider`). The factory reads `settings.LLM_PROVIDER` once and returns the configured implementation (`OllamaLLMProvider` or `OpenAILLMProvider`). Routes remain completely ignorant of which vendor is running.
3. **Flawless test isolation via `dependency_overrides`**: When using global singletons, mocking an external service or running an in-memory database requires monkey-patching Python modules (`unittest.mock.patch`). Monkey-patching is fragile, prone to leaking across concurrent tests, and fails when references are imported directly via `from module import instance`. In contrast, FastAPI allows explicit overrides at the application level:
   ```python
   app.dependency_overrides[get_settings] = lambda: test_settings
   app.dependency_overrides[get_db] = override_get_db
   app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider()
   ```
   Every route and sub-dependency in the dependency graph immediately receives the test doubles with zero monkey-patching.

## Alternatives considered
| Option | Why rejected |
|---|---|
| Global singletons (`llm_client = OpenAI()`, `db = Session()`) | Impossible to cleanly mock in parallel tests; causes database session leaks across concurrent async requests; tightly couples code to specific vendors. |
| Third-party DI containers (`dependency-injector`, `pinject`) | Adds unnecessary external dependencies, heavy boilerplate, and steep learning curves when FastAPI already provides native, first-class DI. |
| Manual manual factory passing in route functions | Requires manually passing configuration, tokens, and database connections through every layer, cluttering handler signatures and duplicating wiring code. |

## Implementation details

Dependencies are defined in `backend/app/dependencies.py`.

### 1. Hierarchical Dependency Graph (`backend/app/dependencies.py`)

Here, `get_current_user` depends on both `get_db` and `get_settings`. FastAPI automatically resolves the entire chain.

```python
# backend/app/dependencies.py
from functools import lru_cache
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import Settings
from app.models.base import AsyncSessionLocal
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.providers.base import LLMProvider, EmbeddingProvider
from app.services.providers.ollama_provider import OllamaLLMProvider
from app.services.providers.openai_provider import OpenAILLMProvider
from app.services.providers.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
from app.services.providers.openai_embedding_provider import OpenAIEmbeddingProvider

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@lru_cache()
def get_settings() -> Settings:
    """Cached application settings instance."""
    return Settings()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session per request and ensure cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_llm_provider(settings: Settings = Depends(get_settings)) -> LLMProvider:
    """Factory returning the configured LLM provider."""
    match settings.LLM_PROVIDER.lower():
        case "ollama":
            return OllamaLLMProvider(settings)
        case "openai":
            return OpenAILLMProvider(settings)
        case _:
            raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

def get_embedding_provider(settings: Settings = Depends(get_settings)) -> EmbeddingProvider:
    """Factory returning the configured embedding provider."""
    match settings.EMBEDDING_PROVIDER.lower():
        case "sentence_transformer":
            return SentenceTransformerEmbeddingProvider(settings)
        case "openai":
            return OpenAIEmbeddingProvider(settings)
        case _:
            raise ValueError(f"Unsupported embedding provider: {settings.EMBEDDING_PROVIDER}")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Decodes JWT token and fetches user from DB using injected settings and db session."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return UserResponse.model_validate(user)
```

### 2. Consuming Dependencies in a Route Handler (`backend/app/routers/quizzes.py`)

The route handler only declares what it needs. FastAPI resolves and passes the instances:

```python
# backend/app/routers/quizzes.py
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user, get_llm_provider
from app.schemas.user import UserResponse
from app.schemas.quiz import GenerateQuizRequest, QuizResponse
from app.services.providers.base import LLMProvider

router = APIRouter()

@router.post("/generate", response_model=QuizResponse)
async def generate_quiz_endpoint(
    request: GenerateQuizRequest,
    current_user: UserResponse = Depends(get_current_user),
    llm: LLMProvider = Depends(get_llm_provider),
):
    # Route handler is cleanly decoupled from DB connection management,
    # JWT decoding, and vendor-specific LLM implementations.
    return await llm.complete(...)
```

### 3. Testing with Dependency Overrides (`tests/integration/test_quizzes.py`)

In tests, dependencies are swapped cleanly without touching application code or mocking globals:

```python
# tests/integration/test_quizzes.py
import pytest
from httpx import AsyncClient
from app.main import app
from app.dependencies import get_db, get_settings, get_llm_provider
from app.config import Settings

class FakeLLMProvider:
    async def complete(self, messages, schema):
        return schema(questions=[{"text": "What is RAG?", "options": ["A", "B"], "correct_index": 0}])

@pytest.mark.asyncio
async def test_generate_quiz_overrides(async_test_session):
    # Override settings for tests
    test_settings = Settings(JWT_SECRET_KEY="test-secret", LLM_PROVIDER="fake")
    app.dependency_overrides[get_settings] = lambda: test_settings
    
    # Override DB to use the test SQLite in-memory transaction
    app.dependency_overrides[get_db] = lambda: async_test_session
    
    # Override LLM provider to avoid calling external LLM
    app.dependency_overrides[get_llm_provider] = lambda: FakeLLMProvider()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/quizzes/generate",
            json={"topic": "RAG architecture", "num_questions": 1},
            headers={"Authorization": "Bearer valid-test-token"}
        )
        assert response.status_code == 200

    # Clean up overrides after test run
    app.dependency_overrides.clear()
```

## Tradeoffs and known limitations
1. **Runtime discovery instead of compile-time**: If a dependency cannot be resolved (e.g. wrong type hint or recursive dependency cycle), the error surfaces when FastAPI boots or on the first incoming request rather than during static import time.
2. **Factory instantiation overhead**: If a factory dependency (such as `get_llm_provider`) creates a heavy client on every invocation, it should either use `@lru_cache()` or register a cached instance at application lifespan startup to avoid recreating connection pools per request.
3. **Implicit context passing**: While dependency injection keeps functions clean, deeply nested dependencies can make tracing the exact origin of a parameter harder for engineers unfamiliar with FastAPI's `Depends` system.
