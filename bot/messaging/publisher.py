"""RabbitMQ event publisher.

Publishes events to the 'trading.events' topic exchange so the API consumer
can relay them to connected Socket.io clients in real-time.

Routing keys:
  rec.new        → new recommendation written to DB
  analysis.done  → analysis scores updated for a symbol
  alert.trigger  → an alert condition was met

Notification routing keys (consumed by notification_worker):
  notify.slack
  notify.email
  notify.sms
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

import pika
import structlog

log = structlog.get_logger()

EXCHANGE = "trading.events"


class EventPublisher:
    """Thread-safe, lazily-connecting RabbitMQ publisher."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or os.getenv("RABBITMQ_URL", "amqp://trader:trader@localhost:5672")
        self._conn: pika.BlockingConnection | None = None
        self._ch: pika.adapters.blocking_connection.BlockingChannel | None = None
        self._lock = threading.Lock()

    def _connect(self) -> None:
        params = pika.URLParameters(self._url)
        self._conn = pika.BlockingConnection(params)
        self._ch = self._conn.channel()
        self._ch.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
        log.info("rabbitmq.publisher.connected", url=self._url)

    def _ensure_connected(self) -> None:
        if self._conn is None or self._conn.is_closed:
            self._connect()

    def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        """Publish *payload* JSON to the topic exchange with *routing_key*."""
        with self._lock:
            try:
                self._ensure_connected()
                self._ch.basic_publish(
                    exchange=EXCHANGE,
                    routing_key=routing_key,
                    body=json.dumps(payload),
                    properties=pika.BasicProperties(
                        delivery_mode=pika.DeliveryMode.Persistent,
                        content_type="application/json",
                    ),
                )
                log.debug("rabbitmq.published", routing_key=routing_key, payload=payload)
            except Exception as exc:
                log.error("rabbitmq.publish_failed", routing_key=routing_key, error=str(exc))
                self._conn = None  # Force reconnect on next call

    def close(self) -> None:
        with self._lock:
            if self._conn and not self._conn.is_closed:
                self._conn.close()


# Module-level singleton — initialised on first use
_publisher: EventPublisher | None = None


def get_publisher() -> EventPublisher:
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher()
    return _publisher
