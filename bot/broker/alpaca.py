"""Alpaca broker implementation — wraps the existing connector.

Phase 3 / Sprint 2
Adapts the legacy BrokerConnector to the new BaseBroker interface so
that all callers can depend on the abstraction.
"""

from __future__ import annotations

from typing import Optional
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import alpaca_trade_api as tradeapi

from broker.base import BaseBroker, OrderResult
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

log = structlog.get_logger()


class AlpacaBroker(BaseBroker):
    """
    Alpaca Markets broker (paper or live depending on ALPACA_BASE_URL).

    Wraps alpaca-trade-api with retry logic on transient errors.
    Paper mode is detected by the presence of 'paper' in the base URL.
    """

    def __init__(
        self,
        api_key: str = ALPACA_API_KEY,
        secret_key: str = ALPACA_SECRET_KEY,
        base_url: str = ALPACA_BASE_URL,
    ) -> None:
        self._api = tradeapi.REST(api_key, secret_key, base_url, api_version="v2")
        self._base_url = base_url

    # ── BaseBroker interface ───────────────────────────────────────────────

    @property
    def is_paper(self) -> bool:
        return "paper" in self._base_url.lower()

    @property
    def name(self) -> str:
        return "alpaca-paper" if self.is_paper else "alpaca-live"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type(Exception), reraise=True)
    def get_account(self) -> dict:
        acct = self._api.get_account()
        return {
            "portfolio_value": float(acct.portfolio_value),
            "cash":            float(acct.cash),
            "equity":          float(acct.equity),
            "unrealized_pl":   float(acct.unrealized_pl),
            "buying_power":    float(acct.buying_power),
            "is_paper":        self.is_paper,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type(Exception), reraise=True)
    def get_positions(self) -> list[dict]:
        positions = self._api.list_positions()
        return [
            {
                "symbol":        p.symbol,
                "qty":           float(p.qty),
                "market_value":  float(p.market_value),
                "current_price": float(p.current_price),
                "avg_entry_price": float(p.avg_entry_price),
                "unrealized_pl": float(p.unrealized_pl),
            }
            for p in positions
        ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type(Exception), reraise=True)
    def get_position(self, symbol: str) -> Optional[dict]:
        try:
            p = self._api.get_position(symbol)
            return {
                "symbol":        p.symbol,
                "qty":           float(p.qty),
                "market_value":  float(p.market_value),
                "current_price": float(p.current_price),
                "avg_entry_price": float(p.avg_entry_price),
                "unrealized_pl": float(p.unrealized_pl),
            }
        except Exception:
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type(Exception), reraise=True)
    def place_market_order(self, symbol: str, qty: int, side: str) -> OrderResult:
        if qty <= 0:
            return OrderResult(order_id="", symbol=symbol, side=side, qty=qty,
                               status="rejected", error="qty must be > 0")
        try:
            order = self._api.submit_order(
                symbol=symbol, qty=qty, side=side,
                type="market", time_in_force="day"
            )
            log.info("alpaca.order_placed", symbol=symbol, side=side, qty=qty,
                     order_id=order.id, is_paper=self.is_paper)
            return OrderResult(
                order_id=order.id, symbol=symbol, side=side,
                qty=qty, status=order.status,
            )
        except Exception as exc:
            log.error("alpaca.order_failed", symbol=symbol, error=str(exc))
            return OrderResult(order_id="", symbol=symbol, side=side, qty=qty,
                               status="rejected", error=str(exc))

    def cancel_order(self, order_id: str) -> bool:
        try:
            self._api.cancel_order(order_id)
            return True
        except Exception:
            return False

    def is_market_open(self) -> bool:
        try:
            clock = self._api.get_clock()
            return clock.is_open
        except Exception:
            return False

    def healthcheck(self) -> bool:
        try:
            self._api.get_account()
            return True
        except Exception:
            return False
