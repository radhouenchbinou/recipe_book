"""Email notification via SendGrid API."""

from __future__ import annotations

import os
import json
import httpx
import structlog

from notifications.base import NotificationChannel

log = structlog.get_logger()

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


class EmailNotifier(NotificationChannel):
    """Sends email via SendGrid's transactional mail API."""

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
        to_email: str | None = None,
    ) -> None:
        self._api_key   = api_key   or os.getenv("SENDGRID_API_KEY", "")
        self._from      = from_email or os.getenv("SENDGRID_FROM_EMAIL", "")
        self._to        = to_email   or os.getenv("SENDGRID_TO_EMAIL", "")

    def send(self, title: str, body: str, symbol: str | None = None) -> None:
        if not self._api_key or not self._from or not self._to:
            log.warning("email.notifier.not_configured")
            return

        subject = f"[TradingBot] {title}" + (f" — {symbol}" if symbol else "")
        payload = {
            "personalizations": [{"to": [{"email": self._to}]}],
            "from": {"email": self._from},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }

        try:
            resp = httpx.post(
                SENDGRID_URL,
                content=json.dumps(payload),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            resp.raise_for_status()
            log.info("email.notification_sent", symbol=symbol, to=self._to)
        except Exception as exc:
            log.error("email.notification_failed", error=str(exc))
