# RAG: Cross-Encoder Re-Ranking

## 1. Bi-Encoders vs Cross-Encoders
- **Bi-Encoder (Vector Search)**:
  Encodes the query and document independently into fixed 384-dimensional vectors. Similarity is calculated via cosine similarity or dot product. Fast and scalable ($O(N)$ lookup via vector index), but sacrifices deep cross-attention between words in the query and words in the text.
- **Cross-Encoder**:
  Feeds the query and document *together* into the transformer: `[CLS] Query [SEP] Document [SEP]`. Full cross-attention operates across every token pair, capturing subtle conditions like negation, causal relationships, and qualifiers.

## 2. Two-Stage Retrieval Pattern
1. **Stage 1 (Bi-Encoder + BM25)**: Fast retrieval of top 20 candidate chunks.
2. **Stage 2 (Cross-Encoder)**: Re-scores the 20 candidates using `cross-encoder/ms-marco-MiniLM-L-6-v2`, returning the top 8 chunks to the LLM generation prompt.

This delivers the retrieval accuracy of deep cross-attention while maintaining sub-second query latency.
