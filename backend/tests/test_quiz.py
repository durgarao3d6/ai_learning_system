"""Integration and unit tests for Quiz generation, Attempts, and Grading."""

import pytest

from app.config import Settings
from app.services.crypto_service import decrypt_text, encrypt_text
from app.services.grading_service import GradingService
from app.services.providers.base import Message


class MockLLMProvider:
    """Mock LLM provider for deterministic grading & question generation tests."""

    async def complete(self, messages: list[Message], schema: type):
        from app.schemas.quiz import QuestionGenerated
        from app.services.grading_service import ShortAnswerEvaluation
        from app.services.quiz_generator import GeneratedQuestionsBatch, QuestionVerificationResult

        if schema == GeneratedQuestionsBatch:
            return GeneratedQuestionsBatch(
                questions=[
                    QuestionGenerated(
                        text="What is the capital of France?",
                        type="mcq",
                        options=["Paris", "London", "Berlin", "Madrid"],
                        correct_answer="Paris",
                        explanation="Paris is the capital of France.",
                    ),
                    QuestionGenerated(
                        text="Python is statically typed.",
                        type="true_false",
                        options=["True", "False"],
                        correct_answer="False",
                        explanation="Python is dynamically typed.",
                    ),
                ]
            )
        elif schema == QuestionVerificationResult:
            return QuestionVerificationResult(is_valid=True, reason="Sound question.")
        elif schema == ShortAnswerEvaluation:
            return ShortAnswerEvaluation(score=0.9, feedback="Accurate explanation.")
        raise ValueError(f"Unexpected schema: {schema}")


def test_fernet_crypto(test_settings: Settings):
    """Verify encryption and decryption round-trip."""
    plain = "Option A is correct"
    token = encrypt_text(plain, test_settings)
    assert token != plain
    decrypted = decrypt_text(token, test_settings)
    assert decrypted == plain


@pytest.mark.asyncio
async def test_deterministic_mcq_grading():
    """Verify exact-match logic for MCQ and True/False."""
    grader = GradingService(llm=MockLLMProvider())

    # Correct MCQ match
    is_corr, score, _feedback = await grader.grade_question(
        q_type="mcq",
        submitted="Paris",
        correct_answer="Paris",
        question_text="Capital of France?",
    )
    assert is_corr is True
    assert score == 1.0

    # Case-insensitive match
    is_corr, score, _ = await grader.grade_question(
        q_type="true_false",
        submitted="false",
        correct_answer="False",
        question_text="Python is statically typed.",
    )
    assert is_corr is True
    assert score == 1.0

    # Wrong answer
    is_corr, score, _ = await grader.grade_question(
        q_type="mcq",
        submitted="London",
        correct_answer="Paris",
        question_text="Capital of France?",
    )
    assert is_corr is False
    assert score == 0.0
