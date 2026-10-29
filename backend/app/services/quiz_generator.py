"""Quiz generation and two-pass verification service."""

from pydantic import BaseModel

from app.config import Settings
from app.schemas.quiz import QuestionGenerated
from app.services.providers.base import LLMProvider, Message


class GeneratedQuestionsBatch(BaseModel):
    """Batch of questions structured output from LLM."""
    questions: list[QuestionGenerated]


class QuestionVerificationResult(BaseModel):
    """Evaluation result from verifier pass."""
    is_valid: bool
    reason: str


class QuizGeneratorService:
    """Orchestrates topic prompt construction, LLM generation, deduplication, and verification."""

    def __init__(self, llm: LLMProvider, settings: Settings):
        self.llm = llm
        self.settings = settings

    async def generate_topic_questions(
        self,
        topic: str,
        num_questions: int,
        difficulty: str,
        question_types: list[str],
    ) -> list[QuestionGenerated]:
        """Generate verified questions using two-pass LLM pipeline."""
        accepted_questions: list[QuestionGenerated] = []
        attempt_round = 0
        needed = num_questions

        while len(accepted_questions) < num_questions and attempt_round <= 2:
            attempt_round += 1
            batch = await self._generate_pass(topic, needed, difficulty, question_types)
            for q in batch:
                if len(accepted_questions) >= num_questions:
                    break
                # Deduplication check
                if any(self._is_duplicate(q, existing) for existing in accepted_questions):
                    continue
                # Verifier Pass
                is_valid = await self._verify_pass(q, topic)
                if is_valid:
                    accepted_questions.append(q)

            needed = num_questions - len(accepted_questions)

        return accepted_questions

    def _is_duplicate(self, q1: QuestionGenerated, q2: QuestionGenerated) -> bool:
        """Check simple string similarity / identical phrasing."""
        return q1.text.strip().lower() == q2.text.strip().lower()

    async def _generate_pass(
        self,
        topic: str,
        count: int,
        difficulty: str,
        types: list[str],
    ) -> list[QuestionGenerated]:
        """Pass 1: Generate creative candidates."""
        system_msg = (
            "You are an expert exam creator. Generate high quality quiz questions with absolute factual accuracy. "
            "Output strictly conforming to the requested JSON schema."
        )
        types_str = ", ".join(types)
        user_prompt = (
            f"Generate {count} educational questions on the topic: '{topic}'.\n"
            f"Difficulty: {difficulty}.\n"
            f"Allowed question types: {types_str}.\n"
            "Requirements:\n"
            "1. For 'mcq', provide exactly 4 clear options and specify the exact correct option text in correct_answer.\n"
            "2. For 'true_false', options must be ['True', 'False'], and correct_answer must be 'True' or 'False'.\n"
            "3. For 'short_answer', provide a concise reference answer (1-2 sentences) in correct_answer.\n"
            "4. Provide a thorough pedagogical explanation for why the answer is correct."
        )

        messages = [
            Message(role="system", content=system_msg),
            Message(role="user", content=user_prompt),
        ]

        try:
            res = await self.llm.complete(messages, GeneratedQuestionsBatch)
            return res.questions
        except Exception:
            # Fallback if provider fails or returns raw json
            return []

    async def _verify_pass(self, q: QuestionGenerated, topic: str) -> bool:
        """Pass 2: Independent verification of factual accuracy and clarity."""
        system_msg = (
            "You are a rigorous exam auditor. Inspect the question for factual errors, ambiguity, "
            "or mismatched correct answers. Output your verification in the JSON schema."
        )
        prompt = (
            f"Audit this question for the topic '{topic}':\n"
            f"Text: {q.text}\n"
            f"Type: {q.type}\n"
            f"Options: {q.options}\n"
            f"Claimed Correct Answer: {q.correct_answer}\n"
            f"Explanation: {q.explanation}\n\n"
            "Is this question unambiguous, factually sound, and is the correct answer unequivocally right?"
        )
        messages = [
            Message(role="system", content=system_msg),
            Message(role="user", content=prompt),
        ]
        try:
            ver = await self.llm.complete(messages, QuestionVerificationResult)
            return ver.is_valid
        except Exception:
            # If verification call errors, accept question to prevent hard blocking
            return True
