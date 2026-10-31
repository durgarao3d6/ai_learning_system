"""Violation database model for exam proctoring audit trail."""

import datetime
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.quiz import Attempt


class Violation(Base, TimestampMixin):
    """Proctoring violation event logged during an active exam attempt."""

    __tablename__ = "violations"
    __table_args__ = (
        UniqueConstraint("attempt_id", "seq", name="uq_attempt_seq"),
    )

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
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "tab_switch" | "fullscreen_exit" | "no_face" | "multiple_faces" | "looking_away"
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_strike: Mapped[bool] = mapped_column(nullable=False, default=True)

    attempt: Mapped["Attempt"] = relationship("Attempt", back_populates="violations")
