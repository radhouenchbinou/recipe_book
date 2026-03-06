"""Live trading order executor (paper mode).

Phase 2 / Sprint 2
Wraps RiskGuard + BrokerConnector to execute rebalance orders safely.
All trades go through risk checks before hitting the broker API.
Paper trading only in Phase 1/2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import structlog

from broker.connector import BrokerConnector
from risk.guard import RiskGuard, RiskCheckResult

log = structlog.get_logger()


@dataclass
class OrderResult:
    symbol: str
    action: str           # "buy" | "sell" | "skipped" | "blocked"
    qty: int
    price: float
    order_id: Optional[str] = None
    reason: str = ""
    risk_adjusted: bool = False


@dataclass
class ExecutionReport:
    executed: list[OrderResult] = field(default_factory=list)
    blocked:  list[OrderResult] = field(default_factory=list)
    skipped:  list[OrderResult] = field(default_factory=list)

    @property
    def total_orders(self) -> int:
        return len(self.executed) + len(self.blocked) + len(self.skipped)


class LiveTradeExecutor:
    """
    Executes a list of proposed orders through the broker after
    applying risk checks.  Designed for paper trading (Phase 1/2).

    Parameters
    ----------
    broker : BrokerConnector
        Configured broker connector (paper endpoint).
    guard : RiskGuard
        Risk guard instance with configured thresholds.
    dry_run : bool
        When True, logs all orders but never calls the broker.
    """

    def __init__(
        self,
        broker: BrokerConnector,
        guard: Optional[RiskGuard] = None,
        dry_run: bool = True,
    ) -> None:
        self._broker = broker
        self._guard = guard or RiskGuard()
        self._dry_run = dry_run

    def execute_rebalance(
        self,
        orders: list[dict],
    ) -> ExecutionReport:
        """
        Execute a list of rebalance orders (output of PortfolioRebalancer).

        Each order dict must contain:
            symbol, action ("buy"|"sell"), qty, price

        The executor:
        1. Fetches current portfolio state once.
        2. Scans for stop-loss breaches → appends forced sells.
        3. Processes sells first, then buys (frees up cash).
        4. Risk-checks each order before placing.

        Args:
            orders: List of order dicts from PortfolioRebalancer.

        Returns:
            ExecutionReport with executed / blocked / skipped lists.
        """
        report = ExecutionReport()

        try:
            account   = self._broker.get_account()
            positions = self._broker.get_positions()
            portfolio_value = float(account.get("portfolio_value", 0))
            day_pl          = float(account.get("unrealized_pl", 0))
        except Exception as exc:
            log.error("executor.account_fetch_failed", error=str(exc))
            for o in orders:
                report.blocked.append(OrderResult(
                    symbol=o["symbol"], action=o["action"],
                    qty=o.get("qty", 0), price=o.get("price", 0),
                    reason=f"Account fetch failed: {exc}",
                ))
            return report

        # ── Stop-loss scan ─────────────────────────────────────────────────
        stops = self._guard.scan_positions_for_stop_loss(positions)
        for pos in stops:
            forced_sell = {
                "symbol": pos["symbol"],
                "action": "sell",
                "qty":    int(pos.get("qty", 0)),
                "price":  float(pos.get("current_price", 0)),
                "_forced_stop_loss": True,
            }
            orders = [o for o in orders if o.get("symbol") != pos["symbol"]]
            orders.insert(0, forced_sell)
            log.warning("executor.stop_loss_forced_sell", symbol=pos["symbol"])

        # ── Sells first, then buys ─────────────────────────────────────────
        sells = [o for o in orders if o.get("action") == "sell"]
        buys  = [o for o in orders if o.get("action") == "buy"]

        for order in sells + buys:
            result = self._process_order(order, portfolio_value, positions, day_pl)
            if result.action == "blocked":
                report.blocked.append(result)
            elif result.action == "skipped":
                report.skipped.append(result)
            else:
                report.executed.append(result)

        log.info(
            "executor.rebalance_complete",
            executed=len(report.executed),
            blocked=len(report.blocked),
            skipped=len(report.skipped),
            dry_run=self._dry_run,
        )
        return report

    # ── Private helpers ──────────────────────────────────────────────────────

    def _process_order(
        self,
        order: dict,
        portfolio_value: float,
        positions: list[dict],
        day_pl: float,
    ) -> OrderResult:
        symbol = order["symbol"]
        action = order["action"]
        qty    = int(order.get("qty", 0))
        price  = float(order.get("price", 0))

        if qty <= 0:
            return OrderResult(symbol=symbol, action="skipped", qty=0, price=price,
                               reason="Zero quantity")

        # ── Risk check ────────────────────────────────────────────────────
        if action == "buy":
            check: RiskCheckResult = self._guard.check_buy(
                symbol, qty, price, portfolio_value, positions, day_pl
            )
        else:
            check = self._guard.check_sell(symbol, qty, positions)

        if not check.allowed:
            return OrderResult(symbol=symbol, action="blocked", qty=qty, price=price,
                               reason=check.reason)

        final_qty     = check.adjusted_qty if check.adjusted_qty is not None else qty
        risk_adjusted = final_qty != qty

        if final_qty <= 0:
            return OrderResult(symbol=symbol, action="skipped", qty=0, price=price,
                               reason="Adjusted qty is zero after risk check")

        # ── Execute ───────────────────────────────────────────────────────
        if self._dry_run:
            log.info("executor.dry_run_order", symbol=symbol, action=action,
                     qty=final_qty, price=price)
            return OrderResult(symbol=symbol, action=action, qty=final_qty,
                               price=price, order_id="DRY-RUN",
                               reason=check.reason, risk_adjusted=risk_adjusted)

        try:
            order_resp = self._broker.place_market_order(symbol, final_qty, action)
            order_id = order_resp.get("id", "unknown") if isinstance(order_resp, dict) else str(order_resp)
            log.info("executor.order_placed", symbol=symbol, action=action,
                     qty=final_qty, order_id=order_id)
            return OrderResult(symbol=symbol, action=action, qty=final_qty,
                               price=price, order_id=order_id,
                               reason=check.reason, risk_adjusted=risk_adjusted)
        except Exception as exc:
            log.error("executor.order_failed", symbol=symbol, error=str(exc))
            return OrderResult(symbol=symbol, action="blocked", qty=final_qty,
                               price=price, reason=f"Broker error: {exc}")
