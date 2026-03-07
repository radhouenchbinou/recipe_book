"""Broker router — selects paper vs live broker at runtime.

Phase 3 / Sprint 2
Reads BROKER_MODE env var (or constructor arg) and returns the correct
BaseBroker implementation.  All callers should obtain their broker through
this factory so the switch between paper and live is configuration-only.

Supported modes:
  paper  → AlpacaBroker pointed at paper-api.alpaca.markets (default)
  live   → AlpacaBroker pointed at api.alpaca.markets
  sim    → SimBroker (pure in-memory, no network calls — useful for tests)
"""

from __future__ import annotations

import os
from typing import Optional
import structlog

from broker.base import BaseBroker, OrderResult
from broker.alpaca import AlpacaBroker
from config import ALPACA_API_KEY, ALPACA_SECRET_KEY

log = structlog.get_logger()

_PAPER_URL = "https://paper-api.alpaca.markets"
_LIVE_URL  = "https://api.alpaca.markets"


# ── Sim broker (in-memory, no external calls) ──────────────────────────────

class SimBroker(BaseBroker):
    """
    Simulated broker for unit testing and dry-run scenarios.

    All orders are accepted immediately at the price stored in the internal
    price map.  Account starts with $100,000 cash.
    """

    def __init__(self, prices: Optional[dict[str, float]] = None) -> None:
        self._prices: dict[str, float] = prices or {}
        self._cash: float = 100_000.0
        self._positions: dict[str, dict] = {}
        self._orders: list[dict] = []
        self._order_counter = 0

    # ── BaseBroker interface ───────────────────────────────────────────────

    @property
    def is_paper(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return "sim"

    def get_account(self) -> dict:
        equity = self._cash + sum(
            p["qty"] * self._prices.get(p["symbol"], p["avg_entry_price"])
            for p in self._positions.values()
        )
        return {
            "portfolio_value": equity,
            "cash":            self._cash,
            "equity":          equity,
            "unrealized_pl":   0.0,
            "buying_power":    self._cash,
            "is_paper":        True,
        }

    def get_positions(self) -> list[dict]:
        return list(self._positions.values())

    def get_position(self, symbol: str) -> Optional[dict]:
        return self._positions.get(symbol)

    def place_market_order(self, symbol: str, qty: int, side: str) -> OrderResult:
        if qty <= 0:
            return OrderResult(order_id="", symbol=symbol, side=side, qty=qty,
                               status="rejected", error="qty must be > 0")

        price = self._prices.get(symbol, 100.0)   # default $100 if unknown
        cost  = price * qty
        self._order_counter += 1
        order_id = f"sim-{self._order_counter:04d}"

        if side == "buy":
            if cost > self._cash:
                return OrderResult(order_id="", symbol=symbol, side=side, qty=qty,
                                   status="rejected", error="insufficient cash")
            self._cash -= cost
            if symbol in self._positions:
                pos = self._positions[symbol]
                total_cost = pos["avg_entry_price"] * pos["qty"] + cost
                new_qty    = pos["qty"] + qty
                pos["qty"]             = new_qty
                pos["avg_entry_price"] = total_cost / new_qty
                pos["market_value"]    = new_qty * price
                pos["current_price"]   = price
            else:
                self._positions[symbol] = {
                    "symbol":          symbol,
                    "qty":             qty,
                    "market_value":    cost,
                    "current_price":   price,
                    "avg_entry_price": price,
                    "unrealized_pl":   0.0,
                }

        elif side == "sell":
            pos = self._positions.get(symbol)
            if not pos or pos["qty"] < qty:
                return OrderResult(order_id="", symbol=symbol, side=side, qty=qty,
                                   status="rejected", error="insufficient shares")
            self._cash += price * qty
            pos["qty"] -= qty
            if pos["qty"] == 0:
                del self._positions[symbol]
            else:
                pos["market_value"]  = pos["qty"] * price
                pos["current_price"] = price

        self._orders.append({"order_id": order_id, "symbol": symbol,
                              "side": side, "qty": qty, "price": price})
        log.info("sim_broker.order_placed", symbol=symbol, side=side,
                 qty=qty, price=price, order_id=order_id)
        return OrderResult(order_id=order_id, symbol=symbol, side=side,
                           qty=qty, status="filled", filled_price=price)

    def cancel_order(self, order_id: str) -> bool:
        return False   # sim orders fill immediately

    def is_market_open(self) -> bool:
        return True

    def healthcheck(self) -> bool:
        return True


# ── Router / factory ────────────────────────────────────────────────────────

def get_broker(
    mode: Optional[str] = None,
    api_key: Optional[str] = None,
    secret_key: Optional[str] = None,
) -> BaseBroker:
    """
    Factory: return the appropriate BaseBroker for the given mode.

    Args:
        mode:       "paper" | "live" | "sim".  Defaults to BROKER_MODE env
                    var, falling back to "paper" if unset.
        api_key:    Alpaca API key (falls back to config).
        secret_key: Alpaca secret (falls back to config).

    Returns:
        A fully-initialised BaseBroker.

    Raises:
        ValueError: If mode is unrecognised.
    """
    resolved_mode = (mode or os.getenv("BROKER_MODE", "paper")).lower().strip()
    key    = api_key    or ALPACA_API_KEY
    secret = secret_key or ALPACA_SECRET_KEY

    if resolved_mode == "paper":
        broker = AlpacaBroker(api_key=key, secret_key=secret, base_url=_PAPER_URL)
    elif resolved_mode == "live":
        broker = AlpacaBroker(api_key=key, secret_key=secret, base_url=_LIVE_URL)
    elif resolved_mode == "sim":
        broker = SimBroker()
    else:
        raise ValueError(f"Unknown broker mode: {resolved_mode!r}. "
                         "Choose 'paper', 'live', or 'sim'.")

    log.info("broker_router.selected", broker=broker.name, mode=resolved_mode)
    return broker
