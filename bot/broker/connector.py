"""Alpaca broker connector — paper trading in Phase 1.

Task S1-T3-001
"""

from dataclasses import dataclass
from typing import Optional
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

import alpaca_trade_api as tradeapi
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

log = structlog.get_logger()


@dataclass
class Position:
    symbol: str
    qty: float
    market_value: float
    unrealized_pl: float
    current_price: float


@dataclass
class AccountInfo:
    account_id: str
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    is_paper: bool


class BrokerConnector:
    """Thin wrapper around the Alpaca REST API."""

    def __init__(
        self,
        api_key: str = ALPACA_API_KEY,
        secret_key: str = ALPACA_SECRET_KEY,
        base_url: str = ALPACA_BASE_URL,
    ) -> None:
        self._api = tradeapi.REST(api_key, secret_key, base_url, api_version="v2")
        log.info("broker.connected", base_url=base_url)

    # ── Account ────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def get_account(self) -> AccountInfo:
        """Fetch current account information."""
        acct = self._api.get_account()
        return AccountInfo(
            account_id=acct.id,
            equity=float(acct.equity),
            cash=float(acct.cash),
            buying_power=float(acct.buying_power),
            portfolio_value=float(acct.portfolio_value),
            is_paper=acct.status == "ACTIVE" and ALPACA_BASE_URL.startswith("https://paper"),
        )

    # ── Positions ──────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def get_positions(self) -> list[Position]:
        """Return all open positions."""
        raw = self._api.list_positions()
        return [
            Position(
                symbol=p.symbol,
                qty=float(p.qty),
                market_value=float(p.market_value),
                unrealized_pl=float(p.unrealized_pl),
                current_price=float(p.current_price),
            )
            for p in raw
        ]

    def get_position(self, symbol: str) -> Optional[Position]:
        """Return a single position or None if not held."""
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

    # ── Orders (paper only in Phase 1) ────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def place_market_order(
        self,
        symbol: str,
        qty: float,
        side: str,  # "buy" | "sell"
    ) -> dict:
        """Place a market order. Returns the raw order dict."""
        if side not in ("buy", "sell"):
            raise ValueError(f"Invalid side: {side!r}")

        log.info("broker.order.placing", symbol=symbol, qty=qty, side=side)
        order = self._api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type="market",
            time_in_force="day",
        )
        log.info("broker.order.placed", order_id=order.id, status=order.status)
        return order._raw

    # ── Market status ──────────────────────────────────────────────────────

    def is_market_open(self) -> bool:
        """Return True if the US equity market is currently open."""
        clock = self._api.get_clock()
        return clock.is_open

    def healthcheck(self) -> bool:
        """Return True if the broker API is reachable and authenticated."""
        try:
            self._api.get_account()
            return True
        except Exception as exc:
            log.error("broker.healthcheck.failed", error=str(exc))
            return False
