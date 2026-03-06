"""Portfolio rebalancing engine.

Phase 2 / Sprint 1
Computes target weights from composite scores and generates
rebalancing orders to move the portfolio to those targets.
Still uses paper trading in Phase 2 — live trading in Phase 3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import structlog
from sqlalchemy import text

from broker.connector import BrokerConnector, Position
from db import get_session

log = structlog.get_logger()


@dataclass
class RebalanceOrder:
    ticker: str
    action: str          # buy | sell | hold
    current_qty: float
    target_qty: float
    delta_qty: float     # positive = buy, negative = sell
    current_value: float
    target_value: float
    current_weight: float
    target_weight: float


@dataclass
class RebalancePlan:
    portfolio_value: float
    orders: list[RebalanceOrder]
    cash_required: float   # net cash needed (negative = cash freed)
    rebalance_needed: bool


class PortfolioRebalancer:
    """
    Compute target weights from composite scores, diff against current
    positions, and generate the minimal set of trades to rebalance.
    """

    def __init__(
        self,
        broker: BrokerConnector,
        min_weight_change: float = 0.02,  # ignore changes < 2% of portfolio
        max_single_weight: float = 0.25,  # max 25% in any single position
    ) -> None:
        self._broker = broker
        self._min_weight_change = min_weight_change
        self._max_single_weight = max_single_weight

    def compute_plan(self) -> RebalancePlan:
        """Compute a full rebalancing plan from current scores."""
        account = self._broker.get_account()
        positions = self._broker.get_positions()
        portfolio_value = account.portfolio_value

        target_weights = self._compute_target_weights()
        current_weights = self._compute_current_weights(positions, portfolio_value)

        orders: list[RebalanceOrder] = []
        for ticker, target_w in target_weights.items():
            current_w = current_weights.get(ticker, 0.0)
            delta_w = target_w - current_w

            if abs(delta_w) < self._min_weight_change:
                continue  # change too small to act on

            current_pos = next((p for p in positions if p.symbol == ticker), None)
            current_qty = current_pos.qty if current_pos else 0.0
            current_val = current_pos.market_value if current_pos else 0.0

            target_val = portfolio_value * target_w
            current_price = current_pos.current_price if current_pos else self._get_price(ticker)

            if current_price is None or current_price <= 0:
                log.warning("rebalancer.no_price", ticker=ticker)
                continue

            target_qty = target_val / current_price
            delta_qty = target_qty - current_qty

            action = "buy" if delta_qty > 0 else "sell" if delta_qty < 0 else "hold"

            orders.append(RebalanceOrder(
                ticker=ticker,
                action=action,
                current_qty=round(current_qty, 4),
                target_qty=round(target_qty, 4),
                delta_qty=round(delta_qty, 4),
                current_value=round(current_val, 2),
                target_value=round(target_val, 2),
                current_weight=round(current_w * 100, 2),
                target_weight=round(target_w * 100, 2),
            ))

        cash_required = sum(
            o.delta_qty * (o.target_value / o.target_qty if o.target_qty else 0)
            for o in orders if o.action == "buy"
        ) - sum(
            abs(o.delta_qty) * (o.current_value / o.current_qty if o.current_qty else 0)
            for o in orders if o.action == "sell"
        )

        log.info(
            "rebalancer.plan_computed",
            orders=len(orders),
            cash_required=round(cash_required, 2),
            portfolio_value=portfolio_value,
        )

        return RebalancePlan(
            portfolio_value=portfolio_value,
            orders=orders,
            cash_required=round(cash_required, 2),
            rebalance_needed=len(orders) > 0,
        )

    def _compute_target_weights(self) -> dict[str, float]:
        """
        Derive target weights from latest composite scores.
        Scores are normalised so they sum to the investable fraction (80%),
        keeping 20% in cash as buffer.
        """
        session = get_session()
        try:
            rows = session.execute(
                text("""
                    SELECT DISTINCT ON (s.ticker)
                           s.ticker,
                           a.composite_score
                    FROM   analysis_scores a
                    JOIN   symbols s ON s.id = a.symbol_id
                    WHERE  a.composite_score IS NOT NULL
                    ORDER  BY s.ticker, a.scored_at DESC
                """)
            ).fetchall()
        finally:
            session.close()

        if not rows:
            return {}

        # Only consider bullish symbols (score > 50)
        bullish = [(ticker, score) for ticker, score in rows if score > 50]
        if not bullish:
            return {}

        # Normalise to sum = 0.80 (80% invested, 20% cash buffer)
        total_score = sum(score for _, score in bullish)
        investable = 0.80

        weights: dict[str, float] = {}
        for ticker, score in bullish:
            raw_weight = (score / total_score) * investable
            weights[ticker] = min(raw_weight, self._max_single_weight)

        # Renormalise after capping
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {t: w / total_weight * investable for t, w in weights.items()}

        return weights

    @staticmethod
    def _compute_current_weights(
        positions: list[Position], portfolio_value: float
    ) -> dict[str, float]:
        if portfolio_value <= 0:
            return {}
        return {p.symbol: p.market_value / portfolio_value for p in positions}

    def _get_price(self, ticker: str) -> Optional[float]:
        """Fetch latest close price from DB."""
        session = get_session()
        try:
            row = session.execute(
                text("""
                    SELECT md.close FROM market_data md
                    JOIN   symbols s ON s.id = md.symbol_id
                    WHERE  s.ticker = :ticker
                    ORDER  BY md.trade_date DESC LIMIT 1
                """),
                {"ticker": ticker},
            ).fetchone()
            return float(row[0]) if row else None
        finally:
            session.close()
