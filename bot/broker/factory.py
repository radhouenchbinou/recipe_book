"""Broker factory — returns the configured BaseBroker implementation.

Set the BROKER env var to select the broker:
  BROKER=alpaca  (default) → AlpacaBroker
  BROKER=ib               → IBBroker

IB connection settings (optional env vars):
  IB_HOST=127.0.0.1
  IB_PORT=7497
  IB_CLIENT_ID=1
"""

from __future__ import annotations

import os
import structlog

from broker.base import BaseBroker

log = structlog.get_logger()


def get_broker(broker_type: str | None = None) -> BaseBroker:
    """
    Instantiate and return the configured broker.

    Args:
        broker_type: Override; if None, reads BROKER env var (default 'alpaca').
    """
    broker = (broker_type or os.getenv("BROKER", "alpaca")).lower()

    if broker == "alpaca":
        from broker.alpaca import AlpacaBroker
        log.info("broker.factory", broker="alpaca")
        return AlpacaBroker()

    if broker == "ib":
        from broker.ib import IBBroker
        log.info("broker.factory", broker="ib")
        return IBBroker(
            host=os.getenv("IB_HOST", "127.0.0.1"),
            port=int(os.getenv("IB_PORT", "7497")),
            client_id=int(os.getenv("IB_CLIENT_ID", "1")),
        )

    raise ValueError(f"Unknown broker type: {broker!r}. Valid options: alpaca, ib")
