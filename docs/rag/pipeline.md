# RAG Architecture: Pipeline Walkthrough

## 1. Overview
The LearnSmart Notes RAG (Retrieval-Augmented Generation) pipeline enables students to generate high-fidelity, pedagogically sound quizzes strictly grounded in their uploaded course notes (PDF, DOCX, TXT).

## 2. Pipeline Sequence

```mermaid
flowchart TD
    A[Student Uploads Document] --> B[MIME & Magic Bytes Validation]
    B --> C[Background Ingestion Worker]
    C --> D[Text & Section Extraction]
    D --> E[Heading-Aware Token Chunking]
    E --> F[Dense Embeddings Generation: sentence-transformers]
    F --> G[Vector Store Ingestion: ChromaDB]
    G --> H[Document Status: READY]
    
    I[User Requests Quiz from Notes] --> J[Hybrid Retrieval: Dense Vector + BM25]
    J --> K[Cross-Encoder Re-Ranking: Top 20 to Top 8]
    K --> L[MMR Diversity Filter]
    L --> M[Pass 1: Grounded Question Generation]
    M --> N[Pass 2: Hallucination & Citation Verification]
    N --> O[Fernet Encryption & Quiz Persistence]
```

## 3. Guarantees
1. **Zero Hallucination with Source Attribution**:
   Every generated question references a concrete `source_chunk_id` and document excerpt.
2. **Pedagogical Diversity**:
   Maximal Marginal Relevance (MMR) ensures the generated questions span the full breadth of the notes rather than clustering around a single prominent section.
3. **Double Verification**:
   The verifier pass confirms that the cited excerpt factually supports the correct answer before the question is stored.
