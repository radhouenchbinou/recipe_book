"""Base notification channel interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class NotificationChannel(ABC):
    """Abstract base for all notification channels."""

    @abstractmethod
    def send(self, title: str, body: str, symbol: str | None = None) -> None:
        """Send a notification. Must not raise — log and swallow errors."""
