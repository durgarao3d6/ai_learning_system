"""Quiz, Question, Attempt, and Answer database models."""

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.violation import Violation


class Quiz(Base, TimestampMixin):
    """Quiz container holding questions."""

    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(50), default="topic", nullable=False)  # "topic" | "notes"
    difficulty: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)  # "easy" | "medium" | "hard"
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)

    questions: Mapped[list["Question"]] = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts: Mapped[list["Attempt"]] = relationship("Attempt", back_populates="quiz", cascade="all, delete-orphan")


class Question(Base, TimestampMixin):
    """Individual question within a quiz."""

    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # "mcq" | "true_false" | "short_answer"
    options: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # JSON array of options for MCQ
    answer_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet encrypted correct answer
    explanation_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet encrypted explanation
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")
    answers: Mapped[list["AttemptAnswer"]] = relationship("AttemptAnswer", back_populates="question", cascade="all, delete-orphan")


class Attempt(Base, TimestampMixin):
    """An attempt taken by a user on a quiz."""

    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="not_started",
        nullable=False,
    )  # "not_started" | "in_progress" | "completed" | "auto_submitted"
    mode: Mapped[str] = mapped_column(String(50), default="practice", nullable=False)  # "practice" | "exam"
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_limit_seconds: Mapped[int] = mapped_column(Integer, default=900, nullable=False)
    strike_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_strikes: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="attempts")
    answers: Mapped[list["AttemptAnswer"]] = relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")
    violations: Mapped[list["Violation"]] = relationship("Violation", back_populates="attempt", cascade="all, delete-orphan")


class AttemptAnswer(Base, TimestampMixin):
    """Autosaved answer for a specific question in an attempt."""

    __tablename__ = "attempt_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    attempt: Mapped["Attempt"] = relationship("Attempt", back_populates="answers")
    question: Mapped["Question"] = relationship("Question", back_populates="answers")
