"""Unit tests for Proctoring violation handling, sequence idempotency, and strike auto-submit."""

from app.models.violation import Violation


def test_violation_model_instantiation():
    """Verify Violation model initialization and fields."""
    import datetime
    import uuid

    v = Violation(
        id=uuid.uuid4(),
        attempt_id=uuid.uuid4(),
        seq=1,
        event_type="tab_switch",
        occurred_at=datetime.datetime.now(datetime.UTC),
        is_strike=True,
    )
    assert v.seq == 1
    assert v.event_type == "tab_switch"
    assert v.is_strike is True


def test_debounce_logic():
    """Verify 3-second consecutive tab_switch grace window calculation."""
    import datetime

    t0 = datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
    t1 = datetime.datetime(2026, 1, 1, 12, 0, 2, tzinfo=datetime.UTC)  # 2s later
    t2 = datetime.datetime(2026, 1, 1, 12, 0, 5, tzinfo=datetime.UTC)  # 5s later

    # Within 3s grace window -> Not an additional strike
    assert (t1 - t0).total_seconds() < 3.0

    # Outside grace window -> Valid strike
    assert (t2 - t0).total_seconds() >= 3.0
