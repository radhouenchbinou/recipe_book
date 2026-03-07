"""Tests for the CircuitBreaker utility."""

import time
import pytest
from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, State


def _ok():
    return "ok"


def _fail():
    raise ValueError("boom")


class TestCircuitBreaker:
    def test_closed_state_on_success(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
        assert cb.call(_ok) == "ok"
        assert cb.state == State.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(_fail)
        assert cb.state == State.OPEN

    def test_open_rejects_immediately(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60)
        with pytest.raises(ValueError):
            cb.call(_fail)
        assert cb.state == State.OPEN
        with pytest.raises(CircuitBreakerOpen):
            cb.call(_ok)

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)
        with pytest.raises(ValueError):
            cb.call(_fail)
        time.sleep(0.1)
        # Next call should be allowed (HALF_OPEN probe)
        result = cb.call(_ok)
        assert result == "ok"

    def test_closes_after_success_in_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05, success_threshold=2)
        with pytest.raises(ValueError):
            cb.call(_fail)
        time.sleep(0.1)
        cb.call(_ok)  # HALF_OPEN: 1 success
        cb.call(_ok)  # HALF_OPEN: 2 successes → CLOSED
        assert cb.state == State.CLOSED

    def test_reopens_on_failure_in_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)
        with pytest.raises(ValueError):
            cb.call(_fail)
        time.sleep(0.1)
        with pytest.raises(ValueError):
            cb.call(_fail)  # HALF_OPEN probe fails → re-OPEN
        assert cb.state == State.OPEN
