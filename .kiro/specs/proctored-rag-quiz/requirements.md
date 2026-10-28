# Requirements: Proctored RAG Quiz System

> References: [prd.md](../../../prd.md) | [architecture-revised.md](../../../architecture-revised.md)

---

## 1. Authentication

### User Stories

- As a learner, I want to register with email and password so I can access my personal library and quiz history.
- As a learner, I want to sign in and receive a JWT so I can make authenticated API calls.
- As a learner, I want my session to persist across page refreshes via a refresh token.

### Acceptance Criteria

1.1 `POST /api/v1/auth/register` accepts email + password, hashes the password with argon2, creates a user record, and returns access + refresh tokens.
1.2 `POST /api/v1/auth/login` validates credentials and returns tokens; invalid credentials return 401 with a generic message.
1.3 After 5 consecutive failed login attempts from the same IP, the endpoint returns 429 for 15 minutes.
1.4 Protected endpoints return 401 when no valid token is provided.
1.5 Refresh token flow issues a new access token without requiring re-login.

---

## 2. Document Upload and Ingestion

### User Stories

- As a learner, I want to upload PDF, DOCX, TXT, or MD files so the system can generate quizzes from my notes.
- As a learner, I want to see ingestion progress so I know when my document is ready to use.
- As a learner, I want to delete a document and have its data fully removed.

### Acceptance Criteria

2.1 `POST /api/v1/documents` accepts files up to 50 MB; unsupported types return 415.
2.2 On upload, a Document record is created with status `processing`; ingestion runs in the background.
2.3 Text extraction supports PDF (PyMuPDF), DOCX (python-docx), TXT, and MD; scanned PDFs without a text layer return status `ocr_required`.
2.4 Text is split into chunks of ~500 tokens with 50-token overlap, preserving page number and heading metadata.
2.5 Each chunk is embedded and stored in Chroma; Document status becomes `ready`.
2.6 The client can subscribe to `GET /api/v1/documents/{id}/status` (SSE) to receive status transitions.
2.7 `DELETE /api/v1/documents/{id}` removes the document record, all chunks, and all vectors. Existing quizzes retain their question text but lose source links.

---

## 3. Quiz Generation — Topic Mode

### User Stories

- As a learner, I want to generate a quiz from a typed topic so I can test knowledge without uploading notes.
- As a learner, I want to choose question count, difficulty, and question types so I control what I study.

### Acceptance Criteria

3.1 `POST /api/v1/quizzes/generate` with `mode=topic` accepts: topic string, question count (1–50), difficulty (easy/medium/hard), question types (mcq, true_false, short_answer).
3.2 The backend builds a structured prompt and calls the LLM; response is validated against the question JSON schema.
3.3 Malformed or duplicate questions are removed; if fewer than the requested count remain, the backend retries up to 2 times.
3.4 A verifier LLM pass confirms each answer key is correct; questions failing verification are dropped or regenerated.
3.5 Answer keys are encrypted at rest (Fernet) and never returned to the client before submission.
3.6 The endpoint returns a quiz ID and question count within 30 seconds for up to 10 questions.

---

## 4. Quiz Generation — Notes (RAG) Mode

### User Stories

- As a learner, I want to generate a quiz from my uploaded documents so I can test myself on my own material.
- As a learner, I want each question to cite its source so I can review the relevant passage.

### Acceptance Criteria

4.1 `POST /api/v1/quizzes/generate` with `mode=notes` accepts one or more `document_ids` and an optional sub-topic filter.
4.2 The retrieval pipeline runs hybrid search (vector + BM25), cross-encoder re-rank (top 20 → top 8), then MMR diversity filtering.
4.3 Every generated question includes a `source_chunk_id` referencing a retrieved chunk.
4.4 The verifier pass confirms the cited chunk actually supports the answer; questions failing this check are dropped or regenerated.
4.5 Questions are linked to their source chunks in the database; the results endpoint returns the source passage text.

---

## 5. Attempt Configuration

### User Stories

- As a learner, I want to choose Practice or Exam mode before starting so I can decide how strictly I'm monitored.
- As a learner, I want to set the timer and strike limit so I control exam difficulty.

### Acceptance Criteria

5.1 `POST /api/v1/attempts` accepts `quiz_id`, `mode` (practice/exam), `timer_minutes`, and `strike_limit`; creates an attempt with status `not_started`.
5.2 Exam mode requires `timer_minutes` and `strike_limit` (default 3); practice mode makes them optional.
5.3 The attempt record stores configuration at creation time; later admin changes do not affect in-progress attempts.

---

## 6. Pre-Exam Proctoring Check

### User Stories

- As a learner, I want a pre-exam check to confirm my camera works and I'm visible before the timer starts.
- As a learner, I want to understand what is being monitored and give explicit consent.

### Acceptance Criteria

6.1 The UI requests `getUserMedia` camera permission before entering the check screen.
6.2 MediaPipe and COCO-SSD models are loaded during the pre-check, not on exam start.
6.3 The check verifies: exactly one face detected, face centered in frame, adequate lighting.
6.4 A consent screen lists all monitored signals and what is stored; the user must actively accept before proceeding.
6.5 On fullscreen grant, the attempt transitions to `in_progress` and the timer starts server-side.
6.6 If camera permission is denied or models fail to load, Exam mode is blocked; the user may proceed in Practice mode.

---

## 7. Exam Taking

### User Stories

- As a learner, I want my answers autosaved so a browser refresh doesn't lose my progress.
- As a learner, I want to flag questions and navigate freely within the exam.

### Acceptance Criteria

7.1 `GET /api/v1/quizzes/{id}` returns questions without answer keys or explanations.
7.2 `PUT /api/v1/attempts/{id}/answers` is idempotent; repeated calls with the same answer overwrite, not duplicate.
7.3 The UI autosaves on every answer selection; a network error shows a warning but does not block the exam.
7.4 The exam screen shows current question number, timer countdown, strike counter, and flagged question indicators.
7.5 Copy, paste, right-click, and print keyboard shortcuts are suppressed on the exam screen (deterrent, not hard block).

---

## 8. Violation Detection and Handling

### User Stories

- As a learner, I want clear warnings when I trigger a violation so I understand what happened.
- As an admin, I want violation events logged with timestamps so I can review exam integrity.

### Acceptance Criteria

8.1 The ProctorEngine detects and records: tab hidden (`visibilitychange`), focus lost (`blur` > 2s), fullscreen exited, no face > 5s, multiple faces > 2s, looking away > 8s, phone detected (confidence > 0.6 for 3 consecutive frames).
8.2 Each violation event includes: `type`, `timestamp`, `question_id`, `seq` (client monotonic counter), and optional JPEG snapshot.
8.3 Events are sent to `POST /api/v1/attempts/{id}/violations`; the backend inserts idempotently using `(attempt_id, seq)` uniqueness.
8.4 On violation, the UI shows a blocking overlay and increments the strike counter; the exam is paused until fullscreen is restored.
8.5 A 3-second grace window prevents a single fullscreen-exit/re-enter from counting as a strike.
8.6 When the strike limit is reached, the backend marks the attempt `auto_submitted` and triggers grading.
8.7 The ProctorEngine buffers events locally when offline and flushes on reconnect.

---

## 9. Submission and Grading

### User Stories

- As a learner, I want my exam graded immediately on submission so I see results without delay.
- As a learner, I want LLM-graded feedback on short answers so I understand where I went wrong.

### Acceptance Criteria

9.1 `POST /api/v1/attempts/{id}/submit` is accepted only for attempts with status `in_progress`.
9.2 MCQ and true/false questions are graded by exact key match server-side.
9.3 Short-answer questions are graded by an LLM call comparing the response to the answer key and source chunk; result includes a score (0–1) and brief feedback.
9.4 The backend computes overall score, per-topic breakdown, and violation summary; attempt status becomes `completed`.
9.5 The server-side timer rejects submission if the elapsed time exceeds `timer_minutes + 30s` grace.
9.6 Once finalized, the attempt is locked; further answer saves return 409.

---

## 10. Results Review

### User Stories

- As a learner, I want to see my score, wrong answers, and source passages so I can learn from mistakes.
- As a learner, I want to retake only missed questions or generate similar ones.

### Acceptance Criteria

10.1 `GET /api/v1/attempts/{id}/results` returns: score, time taken, violation summary, per-question breakdown.
10.2 For each incorrect answer the response includes: learner's answer, correct answer, explanation, and source passage text (for notes-mode quizzes).
10.3 The UI provides buttons to bookmark a question, regenerate a similar question, or start a retake attempt with only missed questions.

---

## 11. Progress and Analytics

### User Stories

- As a learner, I want a dashboard showing my weakest topics so I know what to study next.
- As a learner, I want a Smart Quiz that focuses on my weak areas.

### Acceptance Criteria

11.1 `GET /api/v1/analytics/progress` returns: score trend over time, weakest topics (by average accuracy), violation trend.
11.2 `topic_stats` is updated atomically on each attempt finalization.
11.3 Smart Quiz generation applies a weighting bias toward topics where `accuracy < 0.6`.
11.4 The dashboard renders a score trend chart, weak topics list, and violation trend indicator.

---

## 12. Admin Violation Review (optional, Phase 5+)

### Acceptance Criteria

12.1 Admins (role = `admin`) can access `GET /api/v1/admin/attempts/{id}/report` — full event timeline with snapshot thumbnails.
12.2 `PATCH /api/v1/admin/violations/{id}` marks a violation as `false_positive` and recomputes `integrity_status`.
12.3 `PATCH /api/v1/admin/attempts/{id}` sets status to `invalidated` or `approved`.
12.4 Non-admin requests to admin endpoints return 403.
