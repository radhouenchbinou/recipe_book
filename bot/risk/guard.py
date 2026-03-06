"""Live trading risk guard.

Phase 2 / Sprint 1
Enforces position limits, per-trade stop-loss, and a daily loss cap
before any order is placed through the broker.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import structlog

log = structlog.get_logger()


@dataclass
class RiskCheckResult:
    allowed: bool
    reason: str
    adjusted_qty: Optional[int] = None   # may reduce qty instead of blocking


class RiskGuard:
    """
    Evaluates proposed orders against risk parameters and either
    approves, adjusts, or blocks them.

    Parameters
    ----------
    max_position_pct : float
        Maximum single-position size as fraction of portfolio (default 0.10).
    stop_loss_pct : float
        Intra-day loss threshold per position that triggers a forced sell (default 0.05).
    daily_loss_limit_pct : float
        If total portfolio is down more than this fraction today, halt all new buys (default 0.03).
    max_open_positions : int
        Hard cap on the number of simultaneously open positions (default 10).
    """

    def __init__(
        self,
        max_position_pct: float = 0.10,
        stop_loss_pct: float = 0.05,
        daily_loss_limit_pct: float = 0.03,
        max_open_positions: int = 10,
    ) -> None:
        self._max_position_pct = max_position_pct
        self._stop_loss_pct = stop_loss_pct
        self._daily_loss_limit_pct = daily_loss_limit_pct
        self._max_open_positions = max_open_positions

    # ── Public API ───────────────────────────────────────────────────────────

    def check_buy(
        self,
        symbol: str,
        qty: int,
        price: float,
        portfolio_value: float,
        open_positions: list[dict],
        day_pl: float,
    ) -> RiskCheckResult:
        """
        Validate a proposed buy order.

        Args:
            symbol: Ticker symbol.
            qty: Proposed share quantity.
            price: Current share price.
            portfolio_value: Total account value.
            open_positions: List of current position dicts (keys: symbol, market_value).
            day_pl: Today's unrealised P&L (negative = loss).

        Returns:
            RiskCheckResult with allowed flag and reason.
        """
        # 1. Daily loss limit
        if portfolio_value > 0 and abs(day_pl) / portfolio_value >= self._daily_loss_limit_pct and day_pl < 0:
            log.warning("risk.daily_loss_limit_breached", symbol=symbol, day_pl=day_pl)
            return RiskCheckResult(
                allowed=False,
                reason=f"Daily loss limit reached: {day_pl:.2f} ({abs(day_pl)/portfolio_value*100:.1f}% of portfolio)",
            )

        # 2. Open position count
        if len(open_positions) >= self._max_open_positions:
            already_in = any(p.get("symbol") == symbol for p in open_positions)
            if not already_in:
                log.warning("risk.max_positions_reached", symbol=symbol, count=len(open_positions))
                return RiskCheckResult(
                    allowed=False,
                    reason=f"Max open positions ({self._max_open_positions}) already reached",
                )

        # 3. Position size limit — may reduce qty
        order_value = qty * price
        max_value = portfolio_value * self._max_position_pct

        # Add existing position in this symbol
        existing_value = sum(
            p.get("market_value", 0) for p in open_positions if p.get("symbol") == symbol
        )
        total_exposure = existing_value + order_value

        if total_exposure > max_value:
            allowed_value = max(0.0, max_value - existing_value)
            adjusted_qty = int(allowed_value // price) if price > 0 else 0
            if adjusted_qty <= 0:
                log.warning("risk.position_size_exceeded", symbol=symbol, order_value=order_value)
                return RiskCheckResult(
                    allowed=False,
                    reason=f"Position size limit exceeded: existing={existing_value:.0f}, "
                           f"max_allowed={max_value:.0f}",
                )
            log.info("risk.qty_reduced", symbol=symbol, original=qty, adjusted=adjusted_qty)
            return RiskCheckResult(
                allowed=True,
                reason=f"Quantity reduced to stay within {self._max_position_pct*100:.0f}% position limit",
                adjusted_qty=adjusted_qty,
            )

        log.info("risk.buy_approved", symbol=symbol, qty=qty, order_value=order_value)
        return RiskCheckResult(allowed=True, reason="ok", adjusted_qty=qty)

    def check_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
    ) -> RiskCheckResult:
        """
        Determine whether a position should be closed due to stop-loss breach.

        Args:
            symbol: Ticker symbol.
            entry_price: Price at which the position was opened.
            current_price: Current market price.

        Returns:
            RiskCheckResult — allowed=False signals the caller should sell.
        """
        if entry_price <= 0:
            return RiskCheckResult(allowed=True, reason="no entry price available")

        loss_pct = (entry_price - current_price) / entry_price
        if loss_pct >= self._stop_loss_pct:
            log.warning(
                "risk.stop_loss_triggered",
                symbol=symbol,
                entry_price=entry_price,
                current_price=current_price,
                loss_pct=round(loss_pct * 100, 2),
            )
            return RiskCheckResult(
                allowed=False,
                reason=f"Stop-loss triggered: -{loss_pct*100:.1f}% (threshold={self._stop_loss_pct*100:.0f}%)",
            )

        return RiskCheckResult(allowed=True, reason="within stop-loss tolerance")

    def scan_positions_for_stop_loss(
        self, positions: list[dict]
    ) -> list[dict]:
        """
        Scan all open positions and return those that breach stop-loss.

        Each position dict must have keys: symbol, avg_entry_price, current_price, qty.

        Returns:
            List of positions (same dicts) that should be liquidated.
        """
        to_close = []
        for pos in positions:
            symbol = pos.get("symbol", "?")
            entry = float(pos.get("avg_entry_price", 0))
            current = float(pos.get("current_price", 0))
            result = self.check_stop_loss(symbol, entry, current)
            if not result.allowed:
                to_close.append(pos)
        return to_close

    def check_sell(
        self,
        symbol: str,
        qty: int,
        open_positions: list[dict],
    ) -> RiskCheckResult:
        """
        Validate a proposed sell order (always allowed if qty ≤ held qty).

        Args:
            symbol: Ticker symbol.
            qty: Proposed sell quantity.
            open_positions: Current open positions.

        Returns:
            RiskCheckResult.
        """
        held = next(
            (int(p.get("qty", 0)) for p in open_positions if p.get("symbol") == symbol),
            0,
        )
        if qty > held:
            return RiskCheckResult(
                allowed=True,
                reason=f"Adjusted sell qty from {qty} to {held} (available shares)",
                adjusted_qty=held,
            )
        return RiskCheckResult(allowed=True, reason="ok", adjusted_qty=qty)
