"""Abstract base class for broker connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


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


class BaseBroker(ABC):
    """Common interface for all broker connectors (Alpaca, IB, …)."""

    @abstractmethod
    def get_account(self) -> AccountInfo:
        """Return current account summary."""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Return all open positions."""

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Return a single open position, or None if not held."""

    @abstractmethod
    def place_market_order(self, symbol: str, qty: float, side: str) -> dict:
        """Place a market order. *side* must be 'buy' or 'sell'."""

    @abstractmethod
    def is_market_open(self) -> bool:
        """Return True if the market is currently open for trading."""

    @abstractmethod
    def healthcheck(self) -> bool:
        """Return True if the broker API is reachable and authenticated."""
