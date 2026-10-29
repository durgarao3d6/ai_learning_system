# RAG: Hybrid Search (Dense Embeddings + BM25)

## 1. Why Hybrid Retrieval?
Pure vector search (bi-encoders) excels at capturing conceptual semantics and synonyms (e.g., matching "cardiac arrest" with "heart attack"). However, vector search frequently fails when queries contain:
- Exact acronyms (e.g., "AST", "OOM", "FIFO").
- Proper nouns, author names, or mathematical symbols.
- Serial numbers or specialized technical jargon.

BM25 (Best Matching 25) uses inverse document frequency (IDF) and term frequency (TF) to excel at exact keyword matches, but fails at semantic abstraction.

## 2. Reciprocal Rank Fusion (RRF)
To combine both strengths without arbitrary score scale issues, we apply Reciprocal Rank Fusion:

$$RRF(d) = \sum_{m \in \{dense, sparse\}} \frac{1}{k + r_m(d)}$$

Where:
- $r_m(d)$ is the rank of document $d$ in system $m$.
- $k$ is a constant (typically $60$) that smooths out high outliers.

This ensures candidates favored by both semantic similarity and exact keyword overlap are prioritized for re-ranking.
