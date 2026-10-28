# Revised Architecture Plan: Proctored RAG Quiz System

> Architect review of [prd.md](./prd.md) — covers what to keep, what to change, and where v1 is overengineered.

## What the PRD Gets Right

- Use case breakdown maps cleanly to the API surface
- Proctoring design choices (local inference, consecutive-frame confirmation, grace windows) are pragmatic
- Phased roadmap is reasonable

---

## Revisions and Recommendations

### 1. Simplify the Tech Stack for v1

The PRD introduces Celery + Redis + Chroma + PostgreSQL from the start. That's too many moving parts before you have a working product.

Revised approach:
- SQLite + embedded Chroma — no separate vector DB process
- FastAPI `BackgroundTasks` instead of Celery/RQ for ingestion in v1 (documents are small, a queue is overkill until scale demands it)
- Add Redis + Celery only in Phase 5 when async ingestion of large PDFs becomes a real bottleneck

This cuts the local dev stack from 4 services (FastAPI, Redis, Postgres, Chroma) down to 2 (FastAPI, Chroma embedded).

### 2. Tighten the Frontend Architecture

The PRD says "Zustand / Redux" — pick one. Zustand is the right call; Redux adds ceremony without benefit for this scope.

Recommended state split:
- Zustand for global UI state (auth session, exam status, proctoring flags)
- React Query for all server state (quizzes, attempts, documents)
- No Redux

Also add `react-router-dom` v6 explicitly with route guards for auth and exam mode (prevents navigating away mid-exam at the router level).

### 3. Proctoring Engine — Treat it as a Standalone Module

The PRD mentions MediaPipe and COCO-SSD but doesn't define the module boundary. Architect this as a self-contained class:

```ts
ProctorEngine
  .start(attemptId, config)   // begins monitoring, binds all listeners
  .stop()                     // unbinds, flushes buffer
  .onViolation(handler)       // callback for UI to react
  .flush()                    // force-send buffered events
```

This keeps exam-screen components clean and makes the engine testable in isolation. Model loading should happen during UC-06 (pre-check), not on exam start, to avoid a delay when the timer begins.

### 4. RAG Pipeline — Add a Re-ranking Step

The PRD uses vector + BM25 with MMR for diversity. Add a lightweight cross-encoder re-rank step between retrieval and prompting (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`). This improves question relevance from notes, especially for longer documents, and runs fast enough locally.

Revised pipeline:

```
Retrieve (vector + BM25)
  → Re-rank (cross-encoder, top 20 → top 8)
  → MMR diversity filter
  → Prompt
```

### 5. Answer Key Storage — Encrypt at Rest

The PRD says "answer keys never leave the server until submit," which is correct. Go further: store answer keys encrypted at rest (Fernet symmetric encryption, keyed per-quiz). If the DB is ever dumped, keys aren't plaintext.

### 6. Violation Event Schema — Add a Sequence Number

Current schema in PRD:
```
violations: id, attempt_id, type, at, question_id, snapshot_path, false_positive
```

Add a `seq` field (client-assigned monotonic sequence number). This lets the backend detect replay attacks and reordered events when the client flushes a buffered queue after a network drop.

### 7. API Versioning from Day One

The PRD's API surface has no versioning. Add `/api/v1/` prefix now — retrofitting this after a frontend is deployed is painful.

### 8. Open Decisions — Recommendations

| Decision | Recommendation |
|---|---|
| LLM provider | **Ollama for dev** (local, no API key, free); OpenAI/Anthropic switchable via provider interface for prod |
| Embeddings | **`sentence-transformers` local** (`all-MiniLM-L6-v2`, runs in-process); switchable via provider interface |
| Single vs multi-user | Build multi-user auth from day one (schema already supports it), skip Admin UI until Phase 5 |
| DB for v1 | SQLite for dev, but use SQLAlchemy + Alembic from day one so migration to Postgres is one config change |
| Electron later | Design ProctorEngine as a pure JS module now; wrapping in Electron later is then straightforward |

### 9. Provider Abstraction — Design Principle

Both LLM and embeddings must sit behind a thin `Protocol` interface. Business logic (generation, grading, retrieval) depends only on these interfaces — never on a vendor SDK directly. Concrete implementations (`OllamaProvider`, `OpenAIProvider`, `SentenceTransformerProvider`) are instantiated at app startup from config and injected via FastAPI dependency injection.

```python
# services/providers/base.py
class LLMProvider(Protocol):
    async def complete(self, messages: list[Message], schema: type[T]) -> T: ...

class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

Switching provider = one env var change (`LLM_PROVIDER=openai`), zero business logic changes. See `docs/architecture/provider-pattern.md` for full rationale.

---

## Revised Delivery Roadmap

| Phase | Scope | Delta from PRD |
|---|---|---|
| 1. Foundation | Repo, auth, DB (SQLite), React shell + router, CI | Drop Redis/Celery |
| 2. Topic quiz | UC-03, UC-05, UC-07, UC-09, UC-10 | No change |
| 3. Notes RAG | UC-02, UC-04, ingest via BackgroundTasks, re-ranker | Add re-ranker; Celery still deferred |
| 4. Proctoring v1 | UC-06, UC-08, ProctorEngine module, tab/fullscreen/face | ProctorEngine as isolated module |
| 5. Scale + phone | COCO-SSD, snapshots, introduce Celery+Redis, UC-13 | Celery introduced here only |
| 6. Analytics | UC-11, UC-12, smart quizzes | No change |
| 7. Hardening | Security, perf, a11y, Electron option | No change |
