"""The injected clock (I-12). The real clock is never read by a test."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from discotrade.clock import Clock, FixedClock, SystemClock


def test_fixed_clock_returns_its_instant_every_time():
    clock = FixedClock(datetime(2026, 3, 2, 14, 0, tzinfo=UTC))
    assert clock.now() == clock.now() == datetime(2026, 3, 2, 14, 0, tzinfo=UTC)


def test_fixed_clock_normalises_to_utc():
    est = timezone(timedelta(hours=-5))
    clock = FixedClock(datetime(2026, 3, 2, 9, 0, tzinfo=est))
    assert clock.now().tzinfo is UTC
    assert clock.now() == datetime(2026, 3, 2, 14, 0, tzinfo=UTC)


def test_fixed_clock_refuses_a_naive_instant():
    with pytest.raises(ValueError):
        FixedClock(datetime(2026, 3, 2, 14, 0))


def test_both_clocks_satisfy_the_protocol():
    assert isinstance(FixedClock(datetime(2026, 1, 1, tzinfo=UTC)), Clock)
    assert isinstance(SystemClock(), Clock)
