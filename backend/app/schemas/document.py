"""Pydantic schemas for Document Ingestion, Retrieval, and RAG Quiz."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Document metadata returned to client."""
    id: uuid.UUID
    filename: str
    file_type: str
    file_size_bytes: int
    status: str
    error_message: str | None = None
    total_pages: int
    total_chunks: int

    class Config:
        from_attributes = True


class DocumentStatusEvent(BaseModel):
    """SSE payload for document status changes."""
    document_id: uuid.UUID
    status: str
    progress: int = 0
    message: str | None = None


class RetrievedChunk(BaseModel):
    """Chunk result from hybrid search & re-ranking."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    text: str
    score: float
    page_number: int | None = None
    heading: str | None = None


class GenerateNotesQuizRequest(BaseModel):
    """Request to generate quiz grounded in user's uploaded documents."""
    document_ids: list[uuid.UUID] = Field(..., min_length=1, description="List of document IDs to query")
    subtopic_filter: str | None = Field(default=None, description="Optional focus area or keyword query")
    num_questions: int = Field(default=5, ge=1, le=20)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    question_types: list[Literal["mcq", "true_false", "short_answer"]] = ["mcq", "true_false"]
    time_limit_minutes: int = Field(default=15, ge=1, le=180)
