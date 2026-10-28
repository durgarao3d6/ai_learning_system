# Proctored RAG Quiz System: Use Cases and Architecture Plan

Stack: Python (FastAPI) backend, React (Vite) frontend, in-browser proctoring. A .NET variant is noted where it differs.

> **Architect Review:** See [architecture-revised.md](./architecture-revised.md) for stack simplifications, revised RAG pipeline, proctoring module design, and updated delivery roadmap.

## 1. Goals and Scope

**Goal:** a learning and exam system that generates quizzes from a topic or from your own notes (RAG), then runs them in a locked-down, monitored exam session.

**In scope**

- Quiz generation from a topic (LLM knowledge, optionally web-grounded) and from uploaded notes (RAG)
- Exam mode with tab-switch detection, fullscreen lock, webcam face tracking and phone detection
- Server-side grading, explanations with source passages, violation reports, progress tracking

**Out of scope (v1)**

- OS-level lockdown, second-monitor detection, live human proctors, mobile app

**Honest constraint:** a browser can detect and penalize tab switching but cannot physically block it. Strict blocking needs a desktop kiosk app (Electron) or OS-level controls. The plan treats detection plus penalty as the v1 contract.

## 2. Actors

| Actor | Description |
| --- | --- |
| Learner | Uploads notes, generates and takes quizzes, reviews results |
| Admin / Instructor (optional) | Reviews violation reports, manages shared question banks |
| LLM Service | External or local model that generates and verifies questions |
| Proctoring Engine | In-browser module that watches focus, camera and phone presence |

## 3. Use Cases, Step by Step

### UC-01: Register and Sign In

1. User opens the app and chooses Sign Up or Sign In.
2. User submits email and password (or OAuth).
3. Backend validates, hashes the password, creates the account.
4. Backend returns a JWT access token and refresh token.
5. Frontend stores the session and routes to the Library screen.

**Alternate:** invalid credentials produce an error with rate limiting after repeated failures.

### UC-02: Upload and Ingest Notes

1. User opens Library and selects Upload (PDF, DOCX, TXT, MD) or pastes text.
2. Frontend sends the file to `POST /documents`.
3. Backend stores the raw file and creates a Document record with status `processing`.
4. A background worker extracts text (PyMuPDF, python-docx).
5. Worker cleans text and splits it into chunks (about 500 tokens, 50 token overlap), keeping page and heading metadata.
6. Worker embeds each chunk and writes vectors to the vector store.
7. Document status becomes `ready`; the UI updates via polling or server-sent events.

**Alternate:** a scanned PDF with no text layer triggers an OCR step (Tesseract) or a clear error.

### UC-03: Generate a Quiz from a Topic

1. User chooses Create Quiz, then Topic mode, and types a topic (for example, SQL joins).
2. User sets number of questions, difficulty, question types (MCQ, true/false, short answer) and mode.
3. Frontend calls `POST /quizzes/generate` with `mode=topic`.
4. Backend optionally runs web search to gather source passages for grounding.
5. Backend builds a prompt with a strict JSON schema and calls the LLM.
6. Backend validates the JSON, removes malformed or duplicate questions.
7. Verifier pass: a second LLM call checks each answer key; failures are regenerated or dropped.
8. Quiz is saved (answers stored server-side) and the quiz id is returned.

### UC-04: Generate a Quiz from Notes (RAG)

1. User selects one or more documents, optionally a sub-topic or page range.
2. Frontend calls `POST /quizzes/generate` with `mode=notes` and `document_ids`.
3. Backend retrieves top-k relevant chunks (hybrid search: vector plus keyword), with diversity (MMR) so questions cover different parts.
4. Backend sends the chunks plus the question schema to the LLM.
5. Every generated question must cite a `source_chunk_id`.
6. Verifier pass checks that the answer is actually supported by the cited chunk.
7. Quiz is saved with question-to-chunk links and returned.

### UC-05: Configure an Attempt

1. User opens a generated quiz and picks **Practice** or **Exam** mode.
2. Practice: soft warnings, no auto-submit, hints allowed.
3. Exam: fullscreen lock, camera required, strike limit (default 3), timer, auto-submit on limit.
4. User sets the timer and strike limit (exam defaults can be fixed by an admin).
5. User clicks Start; backend creates an Attempt record with status `not_started`.

### UC-06: Pre-Exam Proctoring Check

1. App requests camera permission (`getUserMedia`).
2. Proctoring Engine loads models (MediaPipe face, COCO-SSD) from local assets.
3. App shows a live preview and checks: exactly one face, good lighting, face centered.
4. App explains what is monitored and what is stored; user must accept consent.
5. App requests fullscreen. On success, the Attempt becomes `in_progress` and the timer starts.

**Alternate:** camera denied or models fail to load, so Exam mode is blocked and the user may continue in Practice mode.

### UC-07: Take the Exam

1. Backend returns questions without answer keys.
2. UI shows one question at a time with a timer, progress bar and strike counter.
3. Each answer is autosaved to `PUT /attempts/{id}/answers` so a refresh does not lose progress.
4. User can flag questions and navigate between them.
5. Copy, paste, right-click and print shortcuts are disabled on the exam view (deterrent only).

### UC-08: Detect and Handle Violations

1. Proctoring Engine monitors continuously:
   - Tab hidden (`visibilitychange`) and focus lost (`blur`)
   - Fullscreen exited (`fullscreenchange`)
   - No face for more than N seconds, multiple faces, sustained looking away
   - "cell phone" class detected in the frame
2. On each event the engine records a violation: type, timestamp, question id, optional snapshot thumbnail.
3. UI shows a blocking warning and increments the strike counter; the exam pauses until the user returns to fullscreen.
4. Events are sent live to `POST /attempts/{id}/violations`.
5. At the strike limit the backend marks the attempt `auto_submitted` and grades the current answers.
6. Debounce rules prevent one action from counting as many strikes (for example, a 3 second grace window after fullscreen exit).

### UC-09: Submit and Grade

1. User clicks Submit (or the timer or strikes trigger it).
2. Frontend calls `POST /attempts/{id}/submit`.
3. Backend grades MCQ and true/false by exact key match.
4. Short answers are graded by the LLM against the reference answer and source chunk, returning a score and brief feedback.
5. Backend computes score, per-topic breakdown and the violation summary.
6. Attempt is finalized and locked from further edits.

### UC-10: Review Results

1. Results screen shows score, time taken and violation report.
2. For each wrong answer: your answer, correct answer, explanation, and the exact source passage from your notes.
3. User can bookmark questions, regenerate similar questions, or retake only the missed ones.

### UC-11: Track Progress and Weak Areas

1. Backend aggregates attempts by topic and tag.
2. Dashboard shows score trend, weakest topics and violation trend.
3. User can launch Smart Quiz, which weights retrieval and question selection toward weak topics (optionally with spaced repetition scheduling).

### UC-12: Manage Library and Quizzes

1. User can list, rename, tag and delete documents and quizzes.
2. Deleting a document removes its chunks and vectors; existing quizzes keep their text but lose the source link.
3. User can export quiz results as PDF or CSV.

### UC-13: Review Violations (Admin, optional)

1. Admin opens an attempt report with the event timeline and snapshots.
2. Admin can mark a violation as a false positive and recompute the integrity status.
3. Admin can invalidate or approve the attempt.

## 4. Architecture

### 4.1 Logical View

```
+--------------------------- Browser (React) ---------------------------+
|  Library | Create Quiz | Exam Screen | Results | Progress             |
|                                                                       |
|  State: Zustand / Redux          API client: React Query              |
|  Proctoring Engine (runs locally)                                     |
|    - Visibility / Blur / Fullscreen listeners                         |
|    - MediaPipe Face Detection  - COCO-SSD phone detector              |
|    - Violation queue (retry, offline buffer)                          |
+------------------------------+----------------------------------------+
                               | HTTPS (REST + SSE)
+------------------------------v----------------------------------------+
|                       FastAPI Backend (Python)                          |
|  Auth | Documents | Quizzes | Attempts | Violations | Analytics        |
|                                                                       |
|  Services: Ingestion | Retrieval | Generation | Verification | Grading  |
+--------+------------------+------------------+----------------+------+
         |                  |                  |                |
   PostgreSQL/SQLite   Vector Store      Task Queue        LLM Provider
   (users, quizzes,    (Chroma, later    (Celery/RQ +      (Claude, OpenAI
   attempts, events)   pgvector)         Redis)            or Ollama)
                            |
                      Object Storage (uploaded files, snapshots)
```

### 4.2 Components

| Component | Responsibility | Tech |
| --- | --- | --- |
| Web client | UI, exam flow, state, API calls | React, Vite, TypeScript, React Query, Zustand |
| Proctoring Engine | Local detection of tab, fullscreen, face, phone | Browser APIs, MediaPipe, TensorFlow.js COCO-SSD |
| API layer | Auth, validation, routing | FastAPI, Pydantic |
| Ingestion worker | Extract, chunk, embed documents | PyMuPDF, python-docx, sentence-transformers or OpenAI embeddings |
| Retrieval service | Hybrid search with MMR | Chroma plus BM25 (rank-bm25) |
| Generation service | Prompting, JSON schema, retries | LLM SDK, Pydantic structured output |
| Verification service | Answer-key check against source | Second LLM pass |
| Grading service | Objective and LLM-graded scoring | Python |
| Data store | Relational data | SQLite for dev, PostgreSQL for prod, SQLAlchemy, Alembic |
| Queue | Background jobs | Celery or RQ with Redis |
| File storage | Uploads and snapshots | Local disk, then S3-compatible |

**.NET variant:** ASP.NET Core Web API, EF Core, Semantic Kernel for LLM and embeddings, Hangfire for jobs, Qdrant or pgvector for vectors. The React frontend is unchanged.

### 4.3 Data Model (core tables)

| Table | Key fields |
| --- | --- |
| users | id, email, password\_hash, role, created\_at |
| documents | id, user\_id, title, file\_path, status, page\_count |
| chunks | id, document\_id, text, page, heading, vector\_id |
| quizzes | id, user\_id, mode, topic, difficulty, config\_json |
| questions | id, quiz\_id, type, stem, options\_json, answer\_key, explanation, source\_chunk\_id, topic\_tag |
| attempts | id, quiz\_id, user\_id, mode, status, started\_at, submitted\_at, score, integrity\_status |
| attempt\_answers | attempt\_id, question\_id, answer, is\_correct, score, feedback |
| violations | id, attempt\_id, type, at, question\_id, snapshot\_path, false\_positive |
| topic\_stats | user\_id, topic\_tag, attempts, accuracy, last\_seen |

### 4.4 API Surface

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | /auth/register, /auth/login | Sign up and sign in |
| POST | /documents | Upload and ingest notes |
| GET | /documents, /documents/{id} | List and status |
| DELETE | /documents/{id} | Remove document and vectors |
| POST | /quizzes/generate | Generate from topic or notes |
| GET | /quizzes/{id} | Quiz without answer keys |
| POST | /attempts | Create an attempt |
| PUT | /attempts/{id}/answers | Autosave answers |
| POST | /attempts/{id}/violations | Log a violation event |
| POST | /attempts/{id}/submit | Grade and finalize |
| GET | /attempts/{id}/results | Score, explanations, sources |
| GET | /analytics/progress | Weak topics and trends |

### 4.5 RAG and Generation Pipeline

1. **Ingest:** extract text, normalize, split by headings first, then by size with overlap.
2. **Embed:** one embedding per chunk; store metadata (document, page, heading).
3. **Retrieve:** query = topic or selected sections; run vector plus keyword search, then MMR to diversify.
4. **Prompt:** system prompt fixes the role and rules; user prompt carries chunks and the JSON schema (type, stem, options, answer, explanation, source\_chunk\_id, difficulty).
5. **Generate:** request structured JSON; retry on parse failure.
6. **Validate:** schema check, duplicate detection, option sanity (one correct answer, distinct distractors).
7. **Verify:** second pass asks the model whether the cited chunk supports the answer; drop or regenerate failures.
8. **Store:** answer keys stay server-side only.

### 4.6 Proctoring Design

| Signal | Method | Threshold (configurable) |
| --- | --- | --- |
| Tab switch | visibilitychange | Immediate strike |
| Focus lost | window blur | Strike after 2 seconds |
| Left fullscreen | fullscreenchange | Immediate strike, exam paused |
| No face | MediaPipe, sampled at 2 to 5 fps | Absent for more than 5 seconds |
| Multiple faces | MediaPipe | 2 or more faces for more than 2 seconds |
| Looking away | Head pose from landmarks | Away for more than 8 seconds |
| Phone | COCO-SSD "cell phone" class | Confidence above 0.6 for 3 consecutive frames |

Design rules:

- Run all inference locally; send only events and optional low-resolution snapshots.
- Strikes feed an `integrity_status` (clean, flagged, invalid), so a review step is possible.
- Keep false positives in mind: use consecutive-frame confirmation and a grace window.
- Buffer events locally if the network drops and flush on reconnect.

### 4.7 Security and Privacy

- Answer keys and explanations never leave the server until submit.
- JWT auth, hashed passwords (argon2 or bcrypt), per-user data isolation on every query.
- Rate limiting on generation and auth endpoints; upload size and type limits; malware scan on uploads if shared.
- Prompt-injection defense: treat document text as data, never as instructions.
- Explicit camera consent, a clear retention policy for snapshots, and delete-on-request.
- Server-side timer enforcement, so a manipulated client clock cannot extend the exam.

### 4.8 Non-Functional Targets

| Area | Target |
| --- | --- |
| Quiz generation | 10 questions in under 30 seconds |
| Exam interaction latency | Under 200 ms for answer autosave |
| Proctoring CPU | Under 25 percent on a mid-range laptop |
| Availability | Autosave survives refresh and short network loss |
| Observability | Structured logs, request ids, LLM token and cost tracking |

### 4.9 Deployment

- **Local dev:** Docker Compose with FastAPI, Redis, Postgres and Chroma; Vite dev server.
- **Production:** containerized API and worker on a cloud host, managed Postgres, S3-compatible storage, CDN for the React build and model assets.
- **CI:** lint, unit tests, API tests and a small end-to-end test (Playwright) of the exam flow.

## 5. Delivery Roadmap

| Phase | Scope | Outcome |
| --- | --- | --- |
| 1. Foundation | Repo, auth, DB, React shell, CI | Running skeleton |
| 2. Topic quiz | UC-03, UC-05, UC-07, UC-09, UC-10 | Generate and take a plain quiz |
| 3. Notes RAG | UC-02, UC-04, source citations, verifier pass | Quizzes grounded in your notes |
| 4. Proctoring v1 | UC-06, UC-08 with tab, fullscreen and face checks | Strict exam mode |
| 5. Phone detection and review | COCO-SSD, snapshots, UC-13 | Full integrity report |
| 6. Analytics | UC-11, UC-12, smart quizzes | Weak-area learning loop |
| 7. Hardening | Security review, performance, accessibility, Electron option | Production readiness |

## 6. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| LLM produces wrong answer keys | Verifier pass, source citation, user can flag a question |
| False positives in phone or gaze detection | Consecutive-frame confirmation, admin review, practice mode as fallback |
| Browser cannot truly block tab switching | Detect and penalize; offer Electron kiosk later |
| Camera privacy concerns | Local inference, consent screen, short retention |
| Large PDFs slow ingestion | Background queue with status updates |
| LLM cost growth | Cache generated questions, use smaller models for verification |

## 7. Open Decisions

1. LLM provider: hosted API or local (Ollama)?
2. Embeddings: hosted or local sentence-transformers?
3. Single user (self-discipline tool) or multi-user with admin review?
4. Database for v1: SQLite for speed, or PostgreSQL from day one?
5. Is a desktop (Electron) kiosk build wanted later for stricter lockdown?
