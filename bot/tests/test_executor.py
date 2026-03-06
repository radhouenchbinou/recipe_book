"""Tests for bot/trading/executor.py — Phase 2 Sprint 2"""

import pytest
from unittest.mock import MagicMock, patch

from trading.executor import LiveTradeExecutor, ExecutionReport, OrderResult
from risk.guard import RiskGuard


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _broker(account=None, positions=None):
    b = MagicMock()
    b.get_account.return_value = account or {"portfolio_value": 100_000, "unrealized_pl": 0}
    b.get_positions.return_value = positions or []
    b.place_market_order.return_value = {"id": "mock-order-001"}
    return b


def _executor(broker=None, guard=None, dry_run=True) -> LiveTradeExecutor:
    return LiveTradeExecutor(
        broker=broker or _broker(),
        guard=guard or RiskGuard(),
        dry_run=dry_run,
    )


def _order(symbol="AAPL", action="buy", qty=10, price=150.0) -> dict:
    return {"symbol": symbol, "action": action, "qty": qty, "price": price}


# ── ExecutionReport basics ────────────────────────────────────────────────────

class TestExecutionReport:
    def test_total_orders(self):
        report = ExecutionReport(
            executed=[OrderResult("AAPL", "buy", 10, 150, "ord1")],
            blocked =[OrderResult("SPY",  "buy",  5, 400, reason="blocked")],
            skipped =[OrderResult("GLD",  "buy",  0, 180, reason="zero qty")],
        )
        assert report.total_orders == 3


# ── Dry-run execution ─────────────────────────────────────────────────────────

class TestDryRun:
    def test_buy_approved_in_dry_run(self):
        executor = _executor(dry_run=True)
        report = executor.execute_rebalance([_order("AAPL", "buy", 10, 150)])
        assert len(report.executed) == 1
        assert report.executed[0].order_id == "DRY-RUN"
        assert report.executed[0].action == "buy"

    def test_sell_approved_in_dry_run(self):
        broker = _broker(positions=[{"symbol": "AAPL", "qty": 50, "market_value": 7500, "avg_entry_price": 150, "current_price": 150}])
        executor = _executor(broker=broker, dry_run=True)
        report = executor.execute_rebalance([_order("AAPL", "sell", 20, 150)])
        assert len(report.executed) == 1
        assert report.executed[0].action == "sell"

    def test_zero_qty_skipped(self):
        executor = _executor(dry_run=True)
        report = executor.execute_rebalance([_order("AAPL", "buy", 0, 150)])
        assert len(report.skipped) == 1

    def test_empty_order_list(self):
        executor = _executor(dry_run=True)
        report = executor.execute_rebalance([])
        assert report.total_orders == 0


# ── Risk guard integration ─────────────────────────────────────────────────────

class TestRiskGuardIntegration:
    def test_daily_loss_blocks_buy(self):
        broker = _broker(account={"portfolio_value": 100_000, "unrealized_pl": -4_000})
        guard  = RiskGuard(daily_loss_limit_pct=0.03)
        executor = _executor(broker=broker, guard=guard, dry_run=True)
        report = executor.execute_rebalance([_order("AAPL", "buy", 10, 150)])
        assert len(report.blocked) == 1
        assert "Daily loss" in report.blocked[0].reason

    def test_position_size_reduces_qty(self):
        broker = _broker(account={"portfolio_value": 100_000, "unrealized_pl": 0})
        guard  = RiskGuard(max_position_pct=0.10)
        executor = _executor(broker=broker, guard=guard, dry_run=True)
        # 100 shares @ $200 = $20k = 20% — should be reduced
        report = executor.execute_rebalance([_order("AAPL", "buy", 100, 200)])
        assert len(report.executed) == 1
        assert report.executed[0].risk_adjusted is True
        assert report.executed[0].qty < 100


# ── Stop-loss scan ────────────────────────────────────────────────────────────

class TestStopLossScan:
    def test_stop_loss_forces_sell(self):
        positions = [
            {"symbol": "AAPL", "qty": 20, "market_value": 1860, "avg_entry_price": 150.0, "current_price": 93.0},
        ]
        broker = _broker(
            account={"portfolio_value": 100_000, "unrealized_pl": 0},
            positions=positions,
        )
        guard    = RiskGuard(stop_loss_pct=0.05)
        executor = _executor(broker=broker, guard=guard, dry_run=True)
        # No orders passed — stop-loss detected via scan
        report = executor.execute_rebalance([])
        # AAPL forced sell should be executed
        assert any(r.symbol == "AAPL" and r.action == "sell" for r in report.executed)


# ── Account fetch failure ─────────────────────────────────────────────────────

class TestAccountFailure:
    def test_blocks_all_orders_on_account_error(self):
        broker = MagicMock()
        broker.get_account.side_effect = RuntimeError("broker unreachable")
        executor = _executor(broker=broker, dry_run=True)
        report = executor.execute_rebalance([_order("AAPL"), _order("SPY")])
        assert len(report.blocked) == 2


# ── Sells before buys ─────────────────────────────────────────────────────────

class TestOrderSorting:
    def test_sells_processed_before_buys(self):
        order_log = []
        broker = _broker(positions=[{"symbol": "MSFT", "qty": 30, "market_value": 9000, "avg_entry_price": 300, "current_price": 300}])
        # Patch place_market_order to capture order sequence
        broker.place_market_order.side_effect = lambda sym, qty, side: (
            order_log.append(side) or {"id": "mock"}
        )
        executor = _executor(broker=broker, dry_run=False)
        executor.execute_rebalance([
            _order("AAPL", "buy",  10, 150),
            _order("MSFT", "sell", 10, 300),
        ])
        # Sell should appear before buy in the log
        sell_idx = next((i for i, s in enumerate(order_log) if s == "sell"), None)
        buy_idx  = next((i for i, s in enumerate(order_log) if s == "buy"),  None)
        if sell_idx is not None and buy_idx is not None:
            assert sell_idx < buy_idx
