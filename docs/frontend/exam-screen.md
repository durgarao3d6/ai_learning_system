# Frontend: Exam Screen, Autosave & Offline UX

## 1. Exam Screen UX Architecture
The exam screen handles focused student evaluation with the following constraints:
1. **One Question at a Time**: Minimizes cognitive overload and matches standardized exam interfaces.
2. **Flagging Mechanism**: Allows students to bookmark questions for later review before final submission.
3. **Progress Bar & Question Navigator**: Visual grid showing answered, unanswered, and flagged questions.

## 2. Autosave Strategy & Debouncing
- When a student answers an MCQ or true/false question, the selection is dispatched immediately to the local Zustand `examStore` and saved to `PUT /api/v1/attempts/{id}/answers`.
- For short-answer typing inputs, network requests are debounced by 800ms to avoid flooding the backend on every keystroke.
- **Idempotency**: `PUT /api/v1/attempts/{id}/answers` accepts `question_id` and `answer_text`, performing an `upsert` so repeated calls leave the database in the exact same state.

## 3. Offline & Network Failure Handling
- If a network failure occurs during autosave:
  1. The pending answer is queued in `localStorage`.
  2. A discreet amber warning banner appears: *"Offline: answers saved locally and will sync when connection is restored."*
  3. The final "Submit Exam" button is disabled until all pending autosaves have succeeded, preventing data loss.
