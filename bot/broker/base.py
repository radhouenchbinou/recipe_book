"""Broker abstraction layer — BaseBroker interface.

Phase 3 / Sprint 2
Defines the interface that every broker implementation must satisfy.
This lets the rest of the codebase depend on the abstraction, not the
concrete Alpaca implementation — making it straightforward to add
Interactive Brokers, Tradier, or a dry-run sim broker in the future.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str           # "buy" | "sell"
    qty: int
    status: str         # "accepted" | "filled" | "rejected" | "cancelled"
    filled_price: Optional[float] = None
    error: Optional[str] = None


class BaseBroker(ABC):
    """
    Abstract broker interface.

    All broker implementations must implement every method here.
    Callers should type-annotate against `BaseBroker`, never against a
    concrete subclass, to preserve substitutability.
    """

    # ── Account ────────────────────────────────────────────────────────────

    @abstractmethod
    def get_account(self) -> dict:
        """
        Return account summary.

        Returns:
            dict with keys: portfolio_value, cash, equity, unrealized_pl,
                            buying_power, is_paper.
        """

    @abstractmethod
    def get_positions(self) -> list[dict]:
        """
        Return all open positions.

        Returns:
            List of dicts with keys: symbol, qty, market_value,
                                     current_price, avg_entry_price,
                                     unrealized_pl.
        """

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[dict]:
        """
        Return a single open position, or None if not held.

        Args:
            symbol: Ticker symbol.

        Returns:
            Position dict or None.
        """

    # ── Orders ─────────────────────────────────────────────────────────────

    @abstractmethod
    def place_market_order(self, symbol: str, qty: int, side: str) -> OrderResult:
        """
        Submit a market order.

        Args:
            symbol: Ticker symbol.
            qty:    Number of shares (must be > 0).
            side:   "buy" or "sell".

        Returns:
            OrderResult.
        """

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: Broker order ID string.

        Returns:
            True if cancelled, False if not found / already filled.
        """

    # ── Market status ──────────────────────────────────────────────────────

    @abstractmethod
    def is_market_open(self) -> bool:
        """Return True when the primary market is open for trading."""

    # ── Health ────────────────────────────────────────────────────────────

    @abstractmethod
    def healthcheck(self) -> bool:
        """Return True if the broker API is reachable."""

    # ── Metadata ──────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def is_paper(self) -> bool:
        """True for paper/simulated brokers, False for live."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable broker name (e.g. 'alpaca-paper')."""
