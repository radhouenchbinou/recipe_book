"""Circuit breaker — 3-state machine (CLOSED → OPEN → HALF_OPEN).

Usage:
    cb = CircuitBreaker("yfinance", failure_threshold=5, recovery_timeout=60)
    result = cb.call(yf.download, ticker, period="1d")
"""

from __future__ import annotations

import time
import threading
from enum import Enum
from typing import Any, Callable

import structlog

log = structlog.get_logger()


class State(Enum):
    CLOSED    = "closed"     # normal operation
    OPEN      = "open"       # failing — reject calls immediately
    HALF_OPEN = "half_open"  # probe: allow one call to test recovery


class CircuitBreakerOpen(Exception):
    """Raised when the circuit is open and the call is rejected."""


class CircuitBreaker:
    """Thread-safe circuit breaker.

    Args:
        name:               Identifier for logging.
        failure_threshold:  Consecutive failures before opening.
        recovery_timeout:   Seconds to wait before entering HALF_OPEN.
        success_threshold:  Consecutive successes in HALF_OPEN to close.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> State:
        with self._lock:
            return self._state

    def call(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute *fn* if the circuit is closed or half-open, else raise."""
        with self._lock:
            if self._state == State.OPEN:
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    self._state = State.HALF_OPEN
                    self._success_count = 0
                    log.info("circuit_breaker.half_open", name=self.name)
                else:
                    raise CircuitBreakerOpen(f"Circuit '{self.name}' is OPEN")

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except CircuitBreakerOpen:
            raise
        except Exception as exc:
            self._on_failure(exc)
            raise

    def _on_success(self) -> None:
        with self._lock:
            if self._state == State.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = State.CLOSED
                    self._failure_count = 0
                    log.info("circuit_breaker.closed", name=self.name)
            elif self._state == State.CLOSED:
                self._failure_count = 0  # reset on success

    def _on_failure(self, exc: Exception) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            log.warning(
                "circuit_breaker.failure",
                name=self.name,
                count=self._failure_count,
                error=str(exc),
            )
            if self._state == State.HALF_OPEN or self._failure_count >= self.failure_threshold:
                self._state = State.OPEN
                log.error("circuit_breaker.opened", name=self.name)
