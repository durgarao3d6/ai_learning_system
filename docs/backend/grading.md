# Backend: Grading Engine & Server-Side Timer Enforcement

## 1. Grading Mechanics by Question Type

### Multiple Choice & True/False (Deterministic Exact-Match)
- **Algorithm**: Normalized exact string match.
- Spaces are trimmed, case is lowered, and option keys (e.g. "A", "True") are canonicalized.
- Score is binary: 1.0 (correct) or 0.0 (incorrect).
- Execution is instantaneous and deterministic, requiring zero LLM inference.

### Short Answer (LLM Evaluator)
- Short answers cannot be evaluated by string equality because students express correct concepts using varied terminology, synonyms, and grammatical structures.
- **Evaluation Criteria**:
  The grading prompt provides:
  1. The question text.
  2. The reference answer and explanation.
  3. The student's submitted answer.
  The LLM evaluates semantic completeness and accuracy, returning a float score between `0.0` and `1.0` along with constructive feedback.

```python
class ShortAnswerGrade(BaseModel):
    score: float  # 0.0 to 1.0
    feedback: str
    key_points_covered: list[str]
    missing_points: list[str]
```

## 2. Server-Side Timer Enforcement
- **Threat**: A client could manipulate their local clock or pause JavaScript execution to gain unlimited time.
- **Solution**:
  When an attempt starts (`POST /api/v1/attempts`), the backend records `started_at = func.now()`.
  On submission (`POST /api/v1/attempts/{id}/submit`):
  $$\text{elapsed} = \text{submitted\_at} - \text{started\_at}$$
  If $\text{elapsed} > \text{time\_limit\_seconds} + 30\text{s (grace period for network latency)}$, the attempt is rejected or marked `auto_submitted` at timer expiration.
