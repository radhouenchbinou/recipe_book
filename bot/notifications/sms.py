"""SMS notification via Twilio REST API."""

from __future__ import annotations

import os
import httpx
import structlog

from notifications.base import NotificationChannel

log = structlog.get_logger()


class SMSNotifier(NotificationChannel):
    """Sends SMS via the Twilio Messages API."""

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
        to_number: str | None = None,
    ) -> None:
        self._sid        = account_sid or os.getenv("TWILIO_ACCOUNT_SID", "")
        self._token      = auth_token  or os.getenv("TWILIO_AUTH_TOKEN", "")
        self._from       = from_number or os.getenv("TWILIO_FROM_NUMBER", "")
        self._to         = to_number   or os.getenv("TWILIO_TO_NUMBER", "")

    def send(self, title: str, body: str, symbol: str | None = None) -> None:
        if not all([self._sid, self._token, self._from, self._to]):
            log.warning("sms.notifier.not_configured")
            return

        prefix = f"[{symbol}] " if symbol else ""
        message = f"{prefix}{title}: {body}"[:1600]  # Twilio 1600-char limit

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json"
        try:
            resp = httpx.post(
                url,
                data={"From": self._from, "To": self._to, "Body": message},
                auth=(self._sid, self._token),
                timeout=10,
            )
            resp.raise_for_status()
            log.info("sms.notification_sent", symbol=symbol, to=self._to)
        except Exception as exc:
            log.error("sms.notification_failed", error=str(exc))
