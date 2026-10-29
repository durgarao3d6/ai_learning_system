"""Pydantic schemas for Quiz, Question, Attempt, and Grading."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

# --- Quiz Generation Requests & Responses ---

class GenerateQuizRequest(BaseModel):
    """Request payload to generate a new quiz."""
    topic: str = Field(..., min_length=2, max_length=255, description="Quiz subject or topic")
    num_questions: int = Field(default=5, ge=1, le=20, description="Total number of questions")
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    question_types: list[Literal["mcq", "true_false", "short_answer"]] = ["mcq", "true_false"]
    time_limit_minutes: int = Field(default=15, ge=1, le=180)


class QuestionGenerated(BaseModel):
    """Raw question generated from LLM pass."""
    text: str
    type: Literal["mcq", "true_false", "short_answer"]
    options: list[str] | None = None
    correct_answer: str
    explanation: str


class QuestionPublicResponse(BaseModel):
    """Question schema returned during an active exam (without answers)."""
    id: uuid.UUID
    text: str
    type: str
    options: list[str] | None
    order: int

    class Config:
        from_attributes = True


class QuizPublicResponse(BaseModel):
    """Public quiz details with questions stripped of answer keys."""
    id: uuid.UUID
    title: str
    topic: str
    difficulty: str
    time_limit_minutes: int
    questions: list[QuestionPublicResponse]

    class Config:
        from_attributes = True


# --- Attempt & Autosave Schemas ---

class CreateAttemptRequest(BaseModel):
    """Request to initialize an attempt."""
    quiz_id: uuid.UUID
    mode: Literal["practice", "exam"] = "practice"


class AttemptResponse(BaseModel):
    """Attempt metadata."""
    id: uuid.UUID
    quiz_id: uuid.UUID
    status: str
    mode: str
    time_limit_seconds: int
    total_questions: int

    class Config:
        from_attributes = True


class SaveAnswerRequest(BaseModel):
    """Autosave single answer for a question."""
    question_id: uuid.UUID
    submitted_answer: str
    is_flagged: bool = False


class SaveAnswerResponse(BaseModel):
    """Response confirming answer autosave."""
    id: uuid.UUID
    attempt_id: uuid.UUID
    question_id: uuid.UUID
    submitted_answer: str
    is_flagged: bool

    class Config:
        from_attributes = True


# --- Submit & Results Schemas ---

class QuestionResultResponse(BaseModel):
    """Per-question breakdown in results."""
    question_id: uuid.UUID
    text: str
    type: str
    options: list[str] | None
    submitted_answer: str | None
    correct_answer: str
    explanation: str
    is_correct: bool
    score: float
    feedback: str | None


class AttemptResultResponse(BaseModel):
    """Comprehensive exam score and per-question explanation report."""
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    title: str
    topic: str
    status: str
    score: float
    total_questions: int
    correct_count: int
    percentage: float
    questions: list[QuestionResultResponse]
