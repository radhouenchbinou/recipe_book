"""RabbitMQ notification worker.

Consumes notify.* routing keys from the 'trading.events' exchange and
dispatches to the appropriate notification channel (Slack, Email, SMS).

Run as a standalone process:
    python -m bot.workers.notification_worker
"""

from __future__ import annotations

import json
import os
import sys

import pika
import structlog

# Ensure bot/ is on the path when run as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notifications.slack import SlackNotifier
from notifications.email_notifier import EmailNotifier
from notifications.sms import SMSNotifier

log = structlog.get_logger()

EXCHANGE = "trading.events"
NOTIFY_KEYS = ["notify.slack", "notify.email", "notify.sms"]

_CHANNELS = {
    "notify.slack":  SlackNotifier(),
    "notify.email":  EmailNotifier(),
    "notify.sms":    SMSNotifier(),
}


def _handle(ch, method, _props, body: bytes) -> None:
    try:
        payload = json.loads(body)
        title  = payload.get("title", "Trading Bot Alert")
        msg    = payload.get("body", "")
        symbol = payload.get("symbol")

        channel = _CHANNELS.get(method.routing_key)
        if channel:
            channel.send(title, msg, symbol)

    except Exception as exc:
        log.error("notification_worker.error", error=str(exc))
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    url = os.getenv("RABBITMQ_URL", "amqp://trader:trader@localhost:5672")
    params = pika.URLParameters(url)

    log.info("notification_worker.starting", url=url)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)

    for key in NOTIFY_KEYS:
        q = ch.queue_declare("", exclusive=True)
        ch.queue_bind(q.method.queue, EXCHANGE, key)
        ch.basic_consume(q.method.queue, _handle)

    log.info("notification_worker.ready", routing_keys=NOTIFY_KEYS)
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        ch.stop_consuming()
    conn.close()
    log.info("notification_worker.stopped")


if __name__ == "__main__":
    main()
