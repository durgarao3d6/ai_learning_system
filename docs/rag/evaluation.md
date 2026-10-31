# RAG Evaluation Framework

## 1. Why Dedicated RAG Evaluation?
A RAG pipeline can generate fluent, grammatically flawless questions that are nonetheless:
1. **Factually unsupported** by the student's actual study notes (hallucination).
2. **Poorly targeted** due to retrieval of irrelevant or tangential sections (low Precision@K).
3. **Overly narrow**, repeating questions from the same introductory paragraph while ignoring core chapters (low coverage / recall).

To ensure that questions generated from notes remain dependable and aligned with course content, we evaluate the pipeline against six core metrics.

---

## 2. Quantitative Evaluation Metrics

### A. Retrieval Metrics

| Metric | Definition | Target Threshold |
|---|---|---|
| **Precision@K** | $\frac{\text{Relevant Chunks in Top } K}{K}$ (What fraction of retrieved chunks actually contain the answer?) | $\ge 0.75$ for $K=5$ |
| **Recall@K** | $\frac{\text{Relevant Chunks in Top } K}{\text{Total Ground-Truth Relevant Chunks}}$ | $\ge 0.85$ for $K=8$ |
| **Mean Reciprocal Rank (MRR)** | $\frac{1}{|Q|}\sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$ (How high does the most relevant chunk appear?) | $\ge 0.80$ |

### B. Generation & Grounding Metrics

| Metric | Definition | Target Threshold |
|---|---|---|
| **Faithfulness / Groundedness** | Fraction of claims in the generated question and explanation that can be strictly deduced from the retrieved context. | $1.0$ (Zero hallucination tolerance) |
| **Answer Relevance** | Degree to which the question addresses the requested topic/difficulty rather than tangential trivia. | $\ge 0.90$ |
| **Citation Attribution Rate** | Fraction of questions where the linked `source_chunk_id` contains the exact semantic premise required to answer. | $100\%$ |

---

## 3. Automated Evaluation Harness Implementation

In `backend/tests/test_rag_eval.py`, we implement a deterministic evaluation suite verifying:
1. **Retrieval MRR and Precision**: Ingests reference test documents, runs sample queries with known answer locations, and validates rank ordering.
2. **Faithfulness Auditor**: Feeds generated questions and reference chunks into an evaluator prompt, scoring grounding on a scale from $0.0$ to $1.0$.

```python
# Evaluator scoring contract
class GroundingScore(BaseModel):
    is_supported: bool
    unsupported_claims: list[str]
    confidence_score: float  # 0.0 - 1.0
```

By continuously benchmarking these metrics during CI and model updates, we safeguard against silent regression in question quality.
