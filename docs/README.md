# Documentation Index — Proctored RAG Quiz System

This folder documents **why** every significant technical decision was made.
The goal is that any developer joining the project can read a doc and understand
not just what the code does, but why it was written that way, what alternatives
were considered, and what the tradeoffs are.

## Structure

```
docs/
  architecture/         System-wide design decisions
  backend/              Python / FastAPI patterns
  frontend/             React patterns
  rag/                  RAG pipeline decisions
  proctoring/           In-browser proctoring design
  security/             Security controls and rationale
```

## Quick Links

| Topic | Doc |
|---|---|
| Provider abstraction (LLM + embeddings) | [architecture/provider-pattern.md](architecture/provider-pattern.md) |
| Why SQLite for dev, Postgres for prod | [architecture/db-choices.md](architecture/db-choices.md) |
| Why /api/v1/ prefix from day one | [architecture/api-versioning.md](architecture/api-versioning.md) |
| Why Ollama for dev | [architecture/llm-choices.md](architecture/llm-choices.md) |
| Why local sentence-transformers | [architecture/embedding-choices.md](architecture/embedding-choices.md) |
| FastAPI project layout | [backend/project-structure.md](backend/project-structure.md) |
| Dependency injection pattern | [backend/dependency-injection.md](backend/dependency-injection.md) |
| SQLAlchemy + Alembic setup | [backend/database.md](backend/database.md) |
| JWT auth design | [backend/auth.md](backend/auth.md) |
| Answer key encryption | [security/answer-key-encryption.md](security/answer-key-encryption.md) |
| Quiz generation pipeline | [backend/quiz-generation.md](backend/quiz-generation.md) |
| Grading & timer enforcement | [backend/grading.md](backend/grading.md) |
| Exam screen & autosave UX | [frontend/exam-screen.md](frontend/exam-screen.md) |
| RAG pipeline walkthrough | [rag/pipeline.md](rag/pipeline.md) |
| Heading-aware chunking | [rag/chunking.md](rag/chunking.md) |
| Hybrid retrieval (Vector + BM25) | [rag/retrieval.md](rag/retrieval.md) |
| Cross-encoder re-ranking | [rag/reranking.md](rag/reranking.md) |
| Document ingestion & SSE | [backend/ingestion.md](backend/ingestion.md) |
| RAG pipeline walkthrough | [rag/pipeline.md](rag/pipeline.md) |
| Why cross-encoder re-ranking | [rag/reranking.md](rag/reranking.md) |
| ProctorEngine design | [proctoring/proctor-engine.md](proctoring/proctor-engine.md) |
| Why violation seq numbers | [proctoring/violation-events.md](proctoring/violation-events.md) |
| Frontend state split | [frontend/state-management.md](frontend/state-management.md) |
| Route guards | [frontend/routing.md](frontend/routing.md) |
