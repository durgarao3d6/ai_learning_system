# Tasks: Proctored RAG Quiz System

> References: [requirements.md](./requirements.md) | [design.md](./design.md) | [implementation-plan.md](../../../implementation-plan.md)

---

## Phase 1 — Foundation

- [ ] 1.1 Scaffold `backend/` and `frontend/` directories; add `pyproject.toml` and `package.json`
- [ ] 1.2 SQLAlchemy `users` model + Alembic initial migration
- [ ] 1.3 `POST /api/v1/auth/register` — argon2 hash, JWT access + refresh token response
- [ ] 1.4 `POST /api/v1/auth/login` — credential check, rate limit (5 req/min, 429 after 5 failures)
- [ ] 1.5 `POST /api/v1/auth/refresh` — issue new access token from valid refresh token
- [ ] 1.6 Auth middleware — JWT dependency for protected routes; returns 401 on missing/invalid token
- [ ] 1.7 Request-ID middleware + structured JSON logging
- [ ] 1.8 Vite + React 18 + TypeScript scaffold; eslint + prettier config
- [ ] 1.9 `react-router-dom` v6 setup; `AuthGuard`, `ExamGuard`, `AdminGuard` route wrappers
- [ ] 1.10 Zustand `AuthStore`; Login and Register pages wired to API
- [ ] 1.11 React Query client; shell layout (sidebar: Library, Create Quiz, Progress)
- [ ] 1.12 GitHub Actions CI — ruff, mypy, eslint, tsc, pytest

---

## Phase 2 — Topic Quiz

- [ ] 2.1 SQLAlchemy models: `quizzes`, `questions`, `attempts`, `attempt_answers`; migrations
- [ ] 2.2 Fernet key generation + `answer_key_encrypted` field on `questions`
- [ ] 2.3 `POST /api/v1/quizzes/generate` (`mode=topic`) — prompt builder, OpenAI structured output, Pydantic validation
- [ ] 2.4 Duplicate detection + up to 2 retry rounds for missing questions
- [ ] 2.5 Verifier pass — second LLM call per question; drop/regenerate failures
- [ ] 2.6 `GET /api/v1/quizzes/{id}` — questions without answer keys or explanations
- [ ] 2.7 `POST /api/v1/attempts` — create attempt record (`not_started`)
- [ ] 2.8 `PUT /api/v1/attempts/{id}/answers` — idempotent upsert
- [ ] 2.9 `POST /api/v1/attempts/{id}/submit` — exact-match grading for MCQ/true-false; LLM grading for short-answer; finalize attempt
- [ ] 2.10 Server-side timer enforcement — reject submit if elapsed > timer + 30s
- [ ] 2.11 `GET /api/v1/attempts/{id}/results` — score, per-question feedback, explanations
- [ ] 2.12 Frontend: Create Quiz page (topic mode form)
- [ ] 2.13 Frontend: Practice mode exam screen — one question at a time, progress bar, flag, navigate
- [ ] 2.14 Frontend: autosave on answer selection (debounced PUT); offline warning
- [ ] 2.15 Frontend: Results page — score, wrong answers, explanations

---

## Phase 3 — Notes RAG

- [ ] 3.1 SQLAlchemy models: `documents`, `chunks`; migrations
- [ ] 3.2 `POST /api/v1/documents` — MIME + magic bytes validation; 50 MB limit; create Document(`processing`)
- [ ] 3.3 BackgroundTask ingestion worker — PyMuPDF / python-docx text extraction; `ocr_required` status for scanned PDFs
- [ ] 3.4 Chunking — heading-first split, then ~500 tokens / 50-token overlap; store page + heading metadata
- [ ] 3.5 `sentence-transformers/all-MiniLM-L6-v2` embeddings; write to embedded Chroma; set Document → `ready`
- [ ] 3.6 SSE endpoint `GET /api/v1/documents/{id}/status` — push status transitions
- [ ] 3.7 `GET /api/v1/documents` — list user documents
- [ ] 3.8 `DELETE /api/v1/documents/{id}` — cascade delete chunks + vectors
- [ ] 3.9 Retrieval service — Chroma vector search + BM25 (rank-bm25) merge
- [ ] 3.10 Cross-encoder re-rank (`cross-encoder/ms-marco-MiniLM-L-6-v2`, top 20 → top 8)
- [ ] 3.11 MMR diversity filter on re-ranked results
- [ ] 3.12 `POST /api/v1/quizzes/generate` (`mode=notes`) — inject chunks into prompt; require `source_chunk_id` per question
- [ ] 3.13 Verifier pass — confirm cited chunk supports the answer
- [ ] 3.14 Frontend: Library page — upload widget, document list, SSE-driven status badge
- [ ] 3.15 Frontend: Create Quiz page — Notes mode, document multi-select, sub-topic filter
- [ ] 3.16 Frontend: Results page — source passage display per wrong answer

---

## Phase 4 — Proctoring v1

- [ ] 4.1 `ProctorEngine` class — `.start()`, `.stop()`, `.onViolation()`, `.flush()` interface
- [ ] 4.2 Browser listeners — `visibilitychange` (immediate), `blur` (2s debounce), `fullscreenchange` (3s grace)
- [ ] 4.3 MediaPipe face detection loop at 2–5 fps — violations for no face >5s, multiple faces >2s, gaze away >8s
- [ ] 4.4 Offline event buffer — queue events when POST fails; flush on reconnect
- [ ] 4.5 Zustand `ExamStore` — `strikeCount`, `timerEndsAt`, `isFullscreen`
- [ ] 4.6 Frontend: `PreCheckPage` — camera permission, MediaPipe + COCO-SSD model preload, face preview, lighting check, consent screen, request fullscreen → attempt `in_progress`
- [ ] 4.7 Frontend: `ExamPage` exam mode — strike counter, blocking violation overlay, pause-until-fullscreen logic
- [ ] 4.8 Frontend: suppress copy/paste/right-click/print on exam view
- [ ] 4.9 Frontend: `AttemptConfigPage` — Practice/Exam toggle, timer, strike limit
- [ ] 4.10 `violations` table with `seq` column + unique index on `(attempt_id, seq)`; migration
- [ ] 4.11 `POST /api/v1/attempts/{id}/violations` — idempotent insert by `(attempt_id, seq)`
- [ ] 4.12 Backend auto-submit — on strike limit reached, mark `auto_submitted`, trigger grading
- [ ] 4.13 `ExamGuard` — prevents react-router navigation away from exam route while attempt is `in_progress`

---

## Phase 5 — Phone Detection, Snapshots, Admin Review

- [ ] 5.1 ProctorEngine — TensorFlow.js COCO-SSD; phone strike on confidence > 0.6 for 3 consecutive frames
- [ ] 5.2 ProctorEngine — capture low-res JPEG snapshot on violation; attach base64 to event payload
- [ ] 5.3 Backend — save snapshot to local disk (dev) / S3 (prod); store path in `violations.snapshot_path`
- [ ] 5.4 Introduce Celery + Redis for ingestion if BackgroundTasks bottlenecks under large PDFs
- [ ] 5.5 `GET /api/v1/admin/attempts/{id}/report` — full timeline + snapshot URLs (admin only)
- [ ] 5.6 `PATCH /api/v1/admin/violations/{id}` — set `false_positive=true`; recompute `integrity_status`
- [ ] 5.7 `PATCH /api/v1/admin/attempts/{id}` — set status `invalidated` or `approved`
- [ ] 5.8 Frontend: `AdminReportPage` — event timeline, snapshot thumbnails, false-positive toggle
- [ ] 5.9 `AdminGuard` route wrapper — 403 for non-admin roles

---

## Phase 6 — Analytics and Smart Quiz

- [ ] 6.1 `topic_stats` table; update atomically on each attempt finalization; migration
- [ ] 6.2 `GET /api/v1/analytics/progress` — score trend, weakest topics (accuracy < 0.6), violation trend
- [ ] 6.3 Smart Quiz — weight retrieval and question selection toward weak topics
- [ ] 6.4 Frontend: `ProgressPage` — score trend chart, weak topics list, violation trend, Smart Quiz button
- [ ] 6.5 Frontend: Results page — bookmark question, regenerate similar, retake missed questions
- [ ] 6.6 `GET /api/v1/attempts/{id}/export` — PDF or CSV export of results

---

## Phase 7 — Hardening

- [ ] 7.1 slowapi rate limits — 5 req/min on `/auth/*`, 10 req/min on `/quizzes/generate`
- [ ] 7.2 Upload validation — MIME type + magic bytes; 50 MB limit; malware scan hook
- [ ] 7.3 Prompt injection defense — wrap all document chunks in `<document>` delimiters in every prompt
- [ ] 7.4 Per-user data isolation audit — confirm every service query filters by `user_id`
- [ ] 7.5 Quiz generation caching — cache identical topic + config combos to reduce LLM cost
- [ ] 7.6 WCAG 2.1 AA audit — keyboard navigation on exam screen; screen reader labels on all interactive elements
- [ ] 7.7 Observability — structured logs with request IDs; LLM token + cost tracking per generation call
- [ ] 7.8 Production Docker Compose / manifests — managed Postgres, S3, CDN for React build + model assets
- [ ] 7.9 Playwright E2E test — full flow: register → generate → configure → take exam → results
- [ ] 7.10 Optional: Electron kiosk wrapper for stricter tab-switch lockdown
