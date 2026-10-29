"""Grading service supporting exact-match and LLM evaluation."""

from pydantic import BaseModel, Field

from app.services.providers.base import LLMProvider, Message


class ShortAnswerEvaluation(BaseModel):
    """Structured output for short answer LLM evaluation."""
    score: float = Field(..., ge=0.0, le=1.0, description="Grade from 0.0 to 1.0")
    feedback: str = Field(..., description="Constructive explanation of the score")


class GradingService:
    """Evaluates question responses and calculates exam scores."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def grade_question(
        self,
        q_type: str,
        submitted: str,
        correct_answer: str,
        question_text: str,
    ) -> tuple[bool, float, str]:
        """Grade a submitted response. Returns (is_correct, score, feedback)."""
        submitted_clean = (submitted or "").strip()
        correct_clean = correct_answer.strip()

        if q_type in ("mcq", "true_false"):
            # Deterministic exact match (case-insensitive)
            is_match = submitted_clean.lower() == correct_clean.lower()
            score = 1.0 if is_match else 0.0
            feedback = "Correct" if is_match else f"Expected: {correct_clean}"
            return is_match, score, feedback

        elif q_type == "short_answer":
            if not submitted_clean:
                return False, 0.0, "No answer provided."
            return await self._grade_short_answer(question_text, correct_clean, submitted_clean)

        return False, 0.0, "Unknown question type"

    async def _grade_short_answer(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
    ) -> tuple[bool, float, str]:
        """Evaluate semantic correctness using LLM."""
        system_msg = (
            "You are an impartial exam evaluator. Grade the student's short answer against the reference answer. "
            "Output your evaluation as JSON."
        )
        prompt = (
            f"Question: {question}\n"
            f"Reference Answer: {reference_answer}\n"
            f"Student Answer: {student_answer}\n\n"
            "Award a score from 0.0 to 1.0 based on factual correctness, key concepts covered, and accuracy. "
            "Provide brief helpful feedback."
        )
        messages = [
            Message(role="system", content=system_msg),
            Message(role="user", content=prompt),
        ]
        try:
            eval_res = await self.llm.complete(messages, ShortAnswerEvaluation)
            is_correct = eval_res.score >= 0.7
            return is_correct, eval_res.score, eval_res.feedback
        except Exception:
            # Fallback exact-match heuristic if LLM provider fails
            is_match = reference_answer.lower() in student_answer.lower()
            score = 1.0 if is_match else 0.0
            return is_match, score, "Graded via fallback heuristic."
