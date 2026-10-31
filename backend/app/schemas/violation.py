"""Pydantic schemas for Proctoring Violations and Event Payloads."""

import datetime
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class ViolationEventRequest(BaseModel):
    """Client-dispatched violation event payload."""
    seq: int = Field(..., ge=1, description="Monotonically increasing sequence number")
    event_type: Literal[
        "tab_switch",
        "fullscreen_exit",
        "no_face",
        "multiple_faces",
        "looking_away",
    ]
    occurred_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
    )
    metadata: dict[str, Any] | None = None


class ViolationResponse(BaseModel):
    """Server response acknowledging violation signal."""
    id: uuid.UUID
    attempt_id: uuid.UUID
    seq: int
    event_type: str
    is_strike: bool
    current_strikes: int
    max_strikes: int
    attempt_status: str

    class Config:
        from_attributes = True


class ViolationSummary(BaseModel):
    """Violation summary for attempt results."""
    total_violations: int
    total_strikes: int
    max_strikes: int
    integrity_status: Literal["clean", "warning", "disqualified"]
    timeline: list[dict[str, Any]]
