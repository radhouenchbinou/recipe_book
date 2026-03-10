"""Alpaca Markets broker — implements BaseBroker (paper trading in Phase 1).

Wraps alpaca-trade-api REST client.
"""

from __future__ import annotations

from typing import Optional
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

import alpaca_trade_api as tradeapi

from broker.base import BaseBroker, AccountInfo, Position
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

log = structlog.get_logger()


class AlpacaBroker(BaseBroker):
    """Thin wrapper around the Alpaca REST API."""

    def __init__(
        self,
        api_key: str = ALPACA_API_KEY,
        secret_key: str = ALPACA_SECRET_KEY,
        base_url: str = ALPACA_BASE_URL,
    ) -> None:
        self._api = tradeapi.REST(api_key, secret_key, base_url, api_version="v2")
        log.info("alpaca_broker.connected", base_url=base_url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def get_account(self) -> AccountInfo:
        acct = self._api.get_account()
        return AccountInfo(
            account_id=acct.id,
            equity=float(acct.equity),
            cash=float(acct.cash),
            buying_power=float(acct.buying_power),
            portfolio_value=float(acct.portfolio_value),
            is_paper=ALPACA_BASE_URL.startswith("https://paper"),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def get_positions(self) -> list[Position]:
        return [
            Position(
                symbol=p.symbol,
                qty=float(p.qty),
                market_value=float(p.market_value),
                unrealized_pl=float(p.unrealized_pl),
                current_price=float(p.current_price),
            )
            for p in self._api.list_positions()
        ]

    def get_position(self, symbol: str) -> Optional[Position]:
        try:
            p = self._api.get_position(symbol)
            return Position(
                symbol=p.symbol,
                qty=float(p.qty),
                market_value=float(p.market_value),
                unrealized_pl=float(p.unrealized_pl),
                current_price=float(p.current_price),
            )
        except tradeapi.rest.APIError as exc:
            if "position does not exist" in str(exc).lower():
                return None
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def place_market_order(self, symbol: str, qty: float, side: str) -> dict:
        if side not in ("buy", "sell"):
            raise ValueError(f"Invalid side: {side!r}")
        log.info("alpaca.order.placing", symbol=symbol, qty=qty, side=side)
        order = self._api.submit_order(
            symbol=symbol, qty=qty, side=side, type="market", time_in_force="day",
        )
        log.info("alpaca.order.placed", order_id=order.id, status=order.status)
        return order._raw

    def is_market_open(self) -> bool:
        return self._api.get_clock().is_open

    def healthcheck(self) -> bool:
        try:
            self._api.get_account()
            return True
        except Exception as exc:
            log.error("alpaca.healthcheck.failed", error=str(exc))
            return False
