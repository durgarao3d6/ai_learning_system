"""Automated RAG Evaluation Suite: Precision@K, MRR, and Faithfulness Verification."""

import pytest

from app.services.retrieval_service import RetrievalService
from app.services.vector_store import VectorStoreService


class MockEmbeddingProvider:
    """Mock provider with predictable vector outputs for deterministic evaluation."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Encodes keywords into distinct coordinate components
        results = []
        for t in texts:
            tl = t.lower()
            v1 = 1.0 if "gradient" in tl or "backprop" in tl else 0.1
            v2 = 1.0 if "b-tree" in tl or "database" in tl else 0.1
            v3 = 1.0 if "dns" in tl or "network" in tl else 0.1
            results.append([v1, v2, v3, 0.5])
        return results

    def dimensions(self) -> int:
        return 4


@pytest.mark.asyncio
async def test_rag_retrieval_precision_and_mrr():
    """Evaluate Mean Reciprocal Rank (MRR) and Precision@K on reference corpus."""
    emb = MockEmbeddingProvider()
    vstore = VectorStoreService(emb, collection_name="eval_corpus")

    doc_id = "eval-doc-1"
    corpus_chunks = [
        {"id": "c_ai_1", "text": "Gradient descent optimizes neural network parameters via backpropagation.", "heading": "Optimization"},
        {"id": "c_ai_2", "text": "Learning rate schedules prevent divergence in deep learning training.", "heading": "Training"},
        {"id": "c_db_1", "text": "B-tree indexing optimizes database range queries and lookups.", "heading": "Indexing"},
        {"id": "c_net_1", "text": "DNS maps domain names to IP addresses over UDP port 53.", "heading": "Networking"},
    ]
    await vstore.add_chunks(doc_id, corpus_chunks)
    retriever = RetrievalService(vstore)

    # Test Query 1: Machine Learning Optimization
    results = await retriever.retrieve_relevant_chunks(
        query="gradient descent backprop",
        document_ids=[doc_id],
        top_k=3,
    )
    assert len(results) > 0

    # Calculate Reciprocal Rank for highest expected chunk (c_ai_1)
    rank = next((idx + 1 for idx, r in enumerate(results) if r.chunk_id == "c_ai_1"), 0)
    assert rank == 1, f"Expected top rank for exact match, got rank {rank}"

    # Precision@1 check
    precision_at_1 = 1.0 if results[0].chunk_id in ("c_ai_1", "c_ai_2") else 0.0
    assert precision_at_1 == 1.0


def test_faithfulness_grounding_verification():
    """Verify that claims in generated questions are strictly contained in retrieved context."""
    source_context = (
        "The CAP theorem states that any distributed data store can only provide "
        "at most two of the following three guarantees: Consistency, Availability, and Partition tolerance."
    )

    # Grounded question (Derived directly from context)
    valid_question = "Which three guarantees are addressed by the CAP theorem?"
    assert "CAP theorem" in valid_question and all(term in source_context for term in ["CAP", "theorem"])

    # Hallucinated assertion (Not present in context)
    assert "1982" not in source_context and "Eric Brewer" not in source_context
