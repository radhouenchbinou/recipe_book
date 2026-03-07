"""Slack webhook notification channel."""

from __future__ import annotations

import os
import json
import httpx
import structlog

from notifications.base import NotificationChannel

log = structlog.get_logger()


class SlackNotifier(NotificationChannel):
    """Posts to a Slack Incoming Webhook URL."""

    def __init__(self, webhook_url: str | None = None) -> None:
        self._url = webhook_url or os.getenv("SLACK_WEBHOOK_URL", "")

    def send(self, title: str, body: str, symbol: str | None = None) -> None:
        if not self._url:
            log.warning("slack.notifier.no_webhook")
            return

        text = f"*{title}*"
        if symbol:
            text = f"*[{symbol}] {title}*"
        text += f"\n{body}"

        try:
            resp = httpx.post(
                self._url,
                content=json.dumps({"text": text}),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            log.info("slack.notification_sent", symbol=symbol)
        except Exception as exc:
            log.error("slack.notification_failed", error=str(exc))
