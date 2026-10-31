"""Proctoring violation tracking and audit API router."""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.dependencies import get_current_user, get_db, get_llm_provider, get_settings
from app.models.quiz import Attempt, Quiz
from app.models.user import User
from app.models.violation import Violation
from app.schemas.violation import ViolationEventRequest, ViolationResponse
from app.services.providers.base import LLMProvider

router = APIRouter(prefix="", tags=["proctoring"])


@router.post("/attempts/{attempt_id}/violations", response_model=ViolationResponse)
async def record_violation(
    attempt_id: uuid.UUID,
    body: ViolationEventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    llm: LLMProvider = Depends(get_llm_provider),
) -> ViolationResponse:
    """Record an in-browser proctoring violation signal with sequence & debounce enforcement."""
    # 1. Fetch Attempt with violations loaded
    stmt = (
        select(Attempt)
        .options(
            selectinload(Attempt.violations),
            selectinload(Attempt.quiz).selectinload(Quiz.questions),
            selectinload(Attempt.answers),
        )
        .where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    attempt = res.scalars().first()

    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    if attempt.status not in ("in_progress", "not_started"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot record violations on attempt with status '{attempt.status}'.",
        )

    # 2. Idempotency Check by (attempt_id, seq)
    existing_violation = next((v for v in attempt.violations if v.seq == body.seq), None)
    if existing_violation:
        return ViolationResponse(
            id=existing_violation.id,
            attempt_id=attempt.id,
            seq=existing_violation.seq,
            event_type=existing_violation.event_type,
            is_strike=existing_violation.is_strike,
            current_strikes=attempt.strike_count,
            max_strikes=attempt.max_strikes,
            attempt_status=attempt.status,
        )

    now = datetime.datetime.now(datetime.UTC)
    is_strike = True

    # 3. Server-Side Debounce: 3-second grace window between consecutive tab/blur events
    if attempt.violations:
        last_violation = max(attempt.violations, key=lambda v: v.occurred_at)
        time_diff = (now - last_violation.occurred_at).total_seconds()
        if time_diff < 3.0 and body.event_type in ("tab_switch", "fullscreen_exit"):
            is_strike = False

    # 4. Insert Violation Record
    new_violation = Violation(
        attempt_id=attempt.id,
        seq=body.seq,
        event_type=body.event_type,
        occurred_at=now,
        metadata_json=body.metadata,
        is_strike=is_strike,
    )
    db.add(new_violation)

    # 5. Update Strike Count
    if is_strike:
        attempt.strike_count += 1

    # 6. Check Strike Limit & Trigger Auto-Submission
    if attempt.strike_count >= attempt.max_strikes:
        attempt.status = "auto_submitted"
        attempt.completed_at = now

    await db.commit()
    await db.refresh(new_violation)
    await db.refresh(attempt)

    return ViolationResponse(
        id=new_violation.id,
        attempt_id=attempt.id,
        seq=new_violation.seq,
        event_type=new_violation.event_type,
        is_strike=new_violation.is_strike,
        current_strikes=attempt.strike_count,
        max_strikes=attempt.max_strikes,
        attempt_status=attempt.status,
    )
