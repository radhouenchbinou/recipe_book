"""Multi-symbol drift detection for portfolio rebalancing.

Phase 2 / Sprint 3
Compares current allocations against target weights and identifies
symbols that have drifted beyond the rebalance threshold.
Produces a minimal set of orders to restore target allocations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import structlog

log = structlog.get_logger()

_DRIFT_THRESHOLD  = 0.03   # 3% absolute drift triggers rebalance
_MIN_ORDER_VALUE  = 500.0  # ignore micro orders below this dollar value


@dataclass
class DriftEntry:
    ticker: str
    current_weight: float
    target_weight: float
    drift: float               # current - target (signed)
    abs_drift: float
    needs_rebalance: bool
    action: str                # "buy" | "sell" | "hold"
    order_value: float         # USD to trade (positive always)
    shares: Optional[int] = None   # filled by caller with live price


@dataclass
class DriftReport:
    total_portfolio_value: float
    entries: list[DriftEntry] = field(default_factory=list)
    drift_threshold: float = _DRIFT_THRESHOLD
    needs_rebalance: bool = False

    @property
    def rebalance_count(self) -> int:
        return sum(1 for e in self.entries if e.needs_rebalance)

    @property
    def buys(self) -> list[DriftEntry]:
        return [e for e in self.entries if e.action == "buy" and e.needs_rebalance]

    @property
    def sells(self) -> list[DriftEntry]:
        return [e for e in self.entries if e.action == "sell" and e.needs_rebalance]


class DriftDetector:
    """
    Detects allocation drift and generates a minimal rebalance order list.

    Parameters
    ----------
    drift_threshold : float
        Minimum absolute weight drift (fraction) before triggering a rebalance.
    min_order_value : float
        Orders smaller than this USD amount are suppressed.
    """

    def __init__(
        self,
        drift_threshold: float = _DRIFT_THRESHOLD,
        min_order_value: float = _MIN_ORDER_VALUE,
    ) -> None:
        self._drift_threshold = drift_threshold
        self._min_order_value = min_order_value

    def detect(
        self,
        target_weights: dict[str, float],
        current_positions: list[dict],
        portfolio_value: float,
    ) -> DriftReport:
        """
        Compare target weights against current positions and return a drift report.

        Args:
            target_weights: Map of ticker → target fraction (e.g. {"AAPL": 0.12}).
            current_positions: List of position dicts from broker
                (keys: symbol, market_value, qty, current_price).
            portfolio_value: Total portfolio value in USD.

        Returns:
            DriftReport with per-symbol drift entries and rebalance orders.
        """
        # Build current weight map
        current_values: dict[str, float] = {
            p["symbol"]: float(p.get("market_value", 0))
            for p in current_positions
        }
        current_weights: dict[str, float] = {
            ticker: val / portfolio_value if portfolio_value > 0 else 0.0
            for ticker, val in current_values.items()
        }

        # Union of all tickers (target + held)
        all_tickers = set(target_weights) | set(current_weights)

        entries: list[DriftEntry] = []
        for ticker in sorted(all_tickers):
            current_w = current_weights.get(ticker, 0.0)
            target_w  = target_weights.get(ticker, 0.0)
            drift     = current_w - target_w
            abs_drift = abs(drift)
            needs_reb = abs_drift >= self._drift_threshold

            # Direction: positive drift → overweight → sell; negative → underweight → buy
            if not needs_reb:
                action = "hold"
                order_value = 0.0
            elif drift > 0:
                action = "sell"
                order_value = abs_drift * portfolio_value
            else:
                action = "buy"
                order_value = abs_drift * portfolio_value

            # Suppress tiny orders
            if order_value < self._min_order_value:
                action = "hold"
                order_value = 0.0
                needs_reb = False

            entries.append(DriftEntry(
                ticker=ticker,
                current_weight=round(current_w, 4),
                target_weight=round(target_w, 4),
                drift=round(drift, 4),
                abs_drift=round(abs_drift, 4),
                needs_rebalance=needs_reb,
                action=action,
                order_value=round(order_value, 2),
            ))

        report = DriftReport(
            total_portfolio_value=portfolio_value,
            entries=entries,
            drift_threshold=self._drift_threshold,
            needs_rebalance=any(e.needs_rebalance for e in entries),
        )
        log.info(
            "drift.detection_complete",
            total_symbols=len(entries),
            needs_rebalance=report.rebalance_count,
            portfolio_value=portfolio_value,
        )
        return report

    def to_orders(
        self,
        report: DriftReport,
        price_map: dict[str, float],
    ) -> list[dict]:
        """
        Convert a DriftReport into a list of order dicts for LiveTradeExecutor.

        Args:
            report: DriftReport from detect().
            price_map: Map of ticker → current price.

        Returns:
            List of dicts with keys: symbol, action, qty, price.
        """
        orders = []
        for entry in report.entries:
            if not entry.needs_rebalance or entry.action == "hold":
                continue
            price = price_map.get(entry.ticker, 0.0)
            if price <= 0:
                log.warning("drift.no_price_for_ticker", ticker=entry.ticker)
                continue
            qty = max(1, int(entry.order_value / price))
            orders.append({
                "symbol": entry.ticker,
                "action": entry.action,
                "qty":    qty,
                "price":  price,
            })
        return orders
