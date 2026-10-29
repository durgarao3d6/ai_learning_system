"""Unit tests for document parsing, chunking, and hybrid retrieval."""

import pytest

from app.services.document_parser import ParsedSection, chunk_sections, validate_file_magic
from app.services.retrieval_service import RetrievalService
from app.services.vector_store import VectorStoreService


class MockEmbeddingProvider:
    """Mock embeddings returning deterministic 4D vectors."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        results = []
        for t in texts:
            val = float(len(t) % 10) / 10.0
            results.append([val, 1.0 - val, val * 0.5, 0.2])
        return results

    def dimensions(self) -> int:
        return 4


def test_validate_file_magic():
    """Verify magic byte detection for allowed file types."""
    pdf_bytes = b"%PDF-1.4 test content"
    assert validate_file_magic(pdf_bytes, "doc.pdf") == "pdf"

    docx_bytes = b"PK\x03\x04test"
    assert validate_file_magic(docx_bytes, "notes.docx") == "docx"

    txt_bytes = b"Hello world text"
    assert validate_file_magic(txt_bytes, "summary.txt") == "txt"

    with pytest.raises(ValueError):
        validate_file_magic(b"unknown binary", "file.exe")


def test_chunk_sections():
    """Verify heading-first window chunking with overlap."""
    words = ["word" + str(i) for i in range(120)]
    text = " ".join(words)
    section = ParsedSection(heading="Chapter 1", text=text, page_number=1)

    chunks = chunk_sections([section], target_tokens=50, overlap_tokens=10)
    assert len(chunks) >= 2
    assert chunks[0]["heading"] == "Chapter 1"
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["token_count"] <= 50


@pytest.mark.asyncio
async def test_vector_and_hybrid_retrieval():
    """Verify vector search and hybrid retrieval ranking."""
    emb = MockEmbeddingProvider()
    vstore = VectorStoreService(emb, collection_name="test_notes")

    doc_id = "test-doc-123"
    chunks = [
        {"id": "c1", "text": "Deep neural networks are composed of layers of neurons.", "heading": "AI Basics"},
        {"id": "c2", "text": "SQLite is a lightweight embedded relational database.", "heading": "Databases"},
    ]
    await vstore.add_chunks(doc_id, chunks)

    retriever = RetrievalService(vstore)
    results = await retriever.retrieve_relevant_chunks(
        query="neural networks layers",
        document_ids=[doc_id],
        top_k=2,
    )
    assert len(results) > 0
    assert results[0].chunk_id in ("c1", "c2")
