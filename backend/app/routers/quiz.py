"""Quizzes and Attempts API router."""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.dependencies import get_current_user, get_db, get_llm_provider, get_settings
from app.models.quiz import Attempt, AttemptAnswer, Question, Quiz
from app.models.user import User
from app.schemas.quiz import (
    AttemptResponse,
    AttemptResultResponse,
    CreateAttemptRequest,
    GenerateQuizRequest,
    QuestionPublicResponse,
    QuestionResultResponse,
    QuizPublicResponse,
    SaveAnswerRequest,
    SaveAnswerResponse,
)
from app.services.crypto_service import decrypt_text, encrypt_text
from app.services.grading_service import GradingService
from app.services.providers.base import LLMProvider
from app.services.quiz_generator import QuizGeneratorService

router = APIRouter(prefix="", tags=["quizzes", "attempts"])


# --- Quiz Endpoints ---

@router.post("/quizzes/generate", response_model=QuizPublicResponse)
async def generate_quiz(
    body: GenerateQuizRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    llm: LLMProvider = Depends(get_llm_provider),
) -> QuizPublicResponse:
    """Generate a new quiz on a given topic using verified LLM pipeline."""
    generator = QuizGeneratorService(llm, settings)
    generated_questions = await generator.generate_topic_questions(
        topic=body.topic,
        num_questions=body.num_questions,
        difficulty=body.difficulty,
        question_types=body.question_types,
    )

    if not generated_questions:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate verified questions for this topic.",
        )

    # Persist Quiz
    new_quiz = Quiz(
        user_id=current_user.id,
        title=f"Quiz: {body.topic}",
        topic=body.topic,
        mode="topic",
        difficulty=body.difficulty,
        time_limit_minutes=body.time_limit_minutes,
    )
    db.add(new_quiz)
    await db.flush()

    # Persist Questions with encrypted answer keys
    questions_to_return: list[QuestionPublicResponse] = []
    for idx, q_data in enumerate(generated_questions):
        enc_ans = encrypt_text(q_data.correct_answer, settings)
        enc_exp = encrypt_text(q_data.explanation, settings)

        q_model = Question(
            quiz_id=new_quiz.id,
            text=q_data.text,
            type=q_data.type,
            options=q_data.options,
            answer_key_encrypted=enc_ans,
            explanation_encrypted=enc_exp,
            order=idx,
        )
        db.add(q_model)
        await db.flush()

        questions_to_return.append(
            QuestionPublicResponse(
                id=q_model.id,
                text=q_model.text,
                type=q_model.type,
                options=q_model.options,
                order=q_model.order,
            )
        )

    await db.commit()

    return QuizPublicResponse(
        id=new_quiz.id,
        title=new_quiz.title,
        topic=new_quiz.topic,
        difficulty=new_quiz.difficulty,
        time_limit_minutes=new_quiz.time_limit_minutes,
        questions=questions_to_return,
    )


@router.get("/quizzes/{quiz_id}", response_model=QuizPublicResponse)
async def get_quiz(
    quiz_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizPublicResponse:
    """Retrieve quiz questions stripped of answer keys."""
    stmt = (
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.id == quiz_id)
    )
    result = await db.execute(stmt)
    quiz = result.scalars().first()

    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    sorted_questions = sorted(quiz.questions, key=lambda q: q.order)
    return QuizPublicResponse(
        id=quiz.id,
        title=quiz.title,
        topic=quiz.topic,
        difficulty=quiz.difficulty,
        time_limit_minutes=quiz.time_limit_minutes,
        questions=[
            QuestionPublicResponse(
                id=q.id,
                text=q.text,
                type=q.type,
                options=q.options,
                order=q.order,
            )
            for q in sorted_questions
        ],
    )


# --- Attempt Endpoints ---

@router.post("/attempts", response_model=AttemptResponse)
async def create_attempt(
    body: CreateAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttemptResponse:
    """Create a new attempt session."""
    stmt = (
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.id == body.quiz_id)
    )
    res = await db.execute(stmt)
    quiz = res.scalars().first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    now = datetime.datetime.now(datetime.UTC)
    attempt = Attempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        status="in_progress",
        mode=body.mode,
        total_questions=len(quiz.questions),
        time_limit_seconds=quiz.time_limit_minutes * 60,
        started_at=now,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    return AttemptResponse(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        status=attempt.status,
        mode=attempt.mode,
        time_limit_seconds=attempt.time_limit_seconds,
        total_questions=attempt.total_questions,
    )


@router.put("/attempts/{attempt_id}/answers", response_model=SaveAnswerResponse)
async def save_answer(
    attempt_id: uuid.UUID,
    body: SaveAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SaveAnswerResponse:
    """Idempotently autosave single answer selection or text."""
    # Verify attempt ownership and active status
    stmt = select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
    res = await db.execute(stmt)
    attempt = res.scalars().first()
    if not attempt or attempt.status not in ("in_progress", "not_started"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt is locked or inactive")

    # Upsert answer record
    a_stmt = select(AttemptAnswer).where(
        AttemptAnswer.attempt_id == attempt_id,
        AttemptAnswer.question_id == body.question_id,
    )
    a_res = await db.execute(a_stmt)
    ans = a_res.scalars().first()

    if ans:
        ans.submitted_answer = body.submitted_answer
        ans.is_flagged = body.is_flagged
    else:
        ans = AttemptAnswer(
            attempt_id=attempt_id,
            question_id=body.question_id,
            submitted_answer=body.submitted_answer,
            is_flagged=body.is_flagged,
        )
        db.add(ans)

    await db.commit()
    await db.refresh(ans)

    return SaveAnswerResponse(
        id=ans.id,
        attempt_id=ans.attempt_id,
        question_id=ans.question_id,
        submitted_answer=ans.submitted_answer,
        is_flagged=ans.is_flagged,
    )


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResultResponse)
async def submit_attempt(
    attempt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    llm: LLMProvider = Depends(get_llm_provider),
) -> AttemptResultResponse:
    """Submit attempt, enforce timer, execute grading, and finalize attempt."""
    stmt = (
        select(Attempt)
        .options(
            selectinload(Attempt.quiz).selectinload(Quiz.questions),
            selectinload(Attempt.answers),
        )
        .where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    attempt = res.scalars().first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    now = datetime.datetime.now(datetime.UTC)

    # Server-side timer check: 30s grace period
    if attempt.started_at:
        elapsed_seconds = (now - attempt.started_at).total_seconds()
        grace_limit = attempt.time_limit_seconds + 30
        if elapsed_seconds > grace_limit:
            attempt.status = "auto_submitted"
        else:
            attempt.status = "completed"
    else:
        attempt.status = "completed"

    attempt.completed_at = now

    # Map existing answers by question_id
    answers_by_qid = {a.question_id: a for a in attempt.answers}
    grading = GradingService(llm)
    total_score = 0.0
    correct_count = 0
    results_list: list[QuestionResultResponse] = []

    for q in attempt.quiz.questions:
        dec_ans = decrypt_text(q.answer_key_encrypted, settings)
        dec_exp = decrypt_text(q.explanation_encrypted, settings)
        student_ans_record = answers_by_qid.get(q.id)
        submitted = student_ans_record.submitted_answer if student_ans_record else ""

        is_corr, score, feedback = await grading.grade_question(
            q_type=q.type,
            submitted=submitted,
            correct_answer=dec_ans,
            question_text=q.text,
        )

        total_score += score
        if is_corr:
            correct_count += 1

        if student_ans_record:
            student_ans_record.is_correct = is_corr
            student_ans_record.score = score
            student_ans_record.feedback = feedback
        else:
            new_ans = AttemptAnswer(
                attempt_id=attempt.id,
                question_id=q.id,
                submitted_answer="",
                is_correct=False,
                score=0.0,
                feedback="Not answered",
            )
            db.add(new_ans)

        results_list.append(
            QuestionResultResponse(
                question_id=q.id,
                text=q.text,
                type=q.type,
                options=q.options,
                submitted_answer=submitted,
                correct_answer=dec_ans,
                explanation=dec_exp,
                is_correct=is_corr,
                score=score,
                feedback=feedback,
            )
        )

    attempt.score = total_score
    attempt.correct_count = correct_count
    await db.commit()

    total_q = len(attempt.quiz.questions)
    percentage = round((total_score / total_q) * 100, 1) if total_q > 0 else 0.0

    return AttemptResultResponse(
        attempt_id=attempt.id,
        quiz_id=attempt.quiz.id,
        title=attempt.quiz.title,
        topic=attempt.quiz.topic,
        status=attempt.status,
        score=total_score,
        total_questions=total_q,
        correct_count=correct_count,
        percentage=percentage,
        questions=results_list,
    )


@router.get("/attempts/{attempt_id}/results", response_model=AttemptResultResponse)
async def get_attempt_results(
    attempt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AttemptResultResponse:
    """Retrieve score, feedback, and decrypted explanations for a finished attempt."""
    stmt = (
        select(Attempt)
        .options(
            selectinload(Attempt.quiz).selectinload(Quiz.questions),
            selectinload(Attempt.answers),
        )
        .where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    attempt = res.scalars().first()
    if not attempt or attempt.status not in ("completed", "auto_submitted"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt results not available yet")

    answers_by_qid = {a.question_id: a for a in attempt.answers}
    results_list: list[QuestionResultResponse] = []

    for q in attempt.quiz.questions:
        dec_ans = decrypt_text(q.answer_key_encrypted, settings)
        dec_exp = decrypt_text(q.explanation_encrypted, settings)
        ans_rec = answers_by_qid.get(q.id)

        results_list.append(
            QuestionResultResponse(
                question_id=q.id,
                text=q.text,
                type=q.type,
                options=q.options,
                submitted_answer=ans_rec.submitted_answer if ans_rec else None,
                correct_answer=dec_ans,
                explanation=dec_exp,
                is_correct=ans_rec.is_correct if ans_rec else False,
                score=ans_rec.score if ans_rec else 0.0,
                feedback=ans_rec.feedback if ans_rec else "Not answered",
            )
        )

    total_q = len(attempt.quiz.questions)
    percentage = round(((attempt.score or 0.0) / total_q) * 100, 1) if total_q > 0 else 0.0

    return AttemptResultResponse(
        attempt_id=attempt.id,
        quiz_id=attempt.quiz.id,
        title=attempt.quiz.title,
        topic=attempt.quiz.topic,
        status=attempt.status,
        score=attempt.score or 0.0,
        total_questions=total_q,
        correct_count=attempt.correct_count,
        percentage=percentage,
        questions=results_list,
    )
