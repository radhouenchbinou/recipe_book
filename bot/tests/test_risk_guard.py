"""Tests for bot/risk/guard.py — Phase 2 Sprint 1"""

import pytest
from risk.guard import RiskGuard, RiskCheckResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _guard(**kwargs) -> RiskGuard:
    return RiskGuard(
        max_position_pct=kwargs.get("max_position_pct", 0.10),
        stop_loss_pct=kwargs.get("stop_loss_pct", 0.05),
        daily_loss_limit_pct=kwargs.get("daily_loss_limit_pct", 0.03),
        max_open_positions=kwargs.get("max_open_positions", 10),
    )


def _pos(symbol: str, market_value: float = 5000, qty: int = 50, entry: float = 100.0, current: float = 100.0) -> dict:
    return {
        "symbol": symbol,
        "market_value": market_value,
        "qty": qty,
        "avg_entry_price": entry,
        "current_price": current,
    }


# ── check_buy ─────────────────────────────────────────────────────────────────

class TestCheckBuy:
    def test_simple_buy_approved(self):
        guard = _guard()
        result = guard.check_buy("AAPL", 10, 150.0, 100_000, [], 0.0)
        assert result.allowed is True

    def test_daily_loss_limit_blocks_buy(self):
        guard = _guard(daily_loss_limit_pct=0.03)
        # -5% loss on a $100k portfolio exceeds 3% limit
        result = guard.check_buy("AAPL", 10, 150.0, 100_000, [], day_pl=-5_000)
        assert result.allowed is False
        assert "Daily loss" in result.reason

    def test_daily_loss_limit_not_triggered_on_profit(self):
        guard = _guard(daily_loss_limit_pct=0.03)
        result = guard.check_buy("AAPL", 10, 150.0, 100_000, [], day_pl=1_000)
        assert result.allowed is True

    def test_max_positions_blocks_new_symbol(self):
        guard = _guard(max_open_positions=2)
        positions = [_pos("SPY"), _pos("QQQ")]
        result = guard.check_buy("AAPL", 10, 150.0, 100_000, positions, 0.0)
        assert result.allowed is False
        assert "Max open positions" in result.reason

    def test_max_positions_allows_adding_to_existing(self):
        guard = _guard(max_open_positions=2)
        positions = [_pos("SPY"), _pos("AAPL", market_value=2000)]
        # AAPL already held — should be allowed (within position size)
        result = guard.check_buy("AAPL", 5, 100.0, 100_000, positions, 0.0)
        assert result.allowed is True

    def test_position_size_reduces_qty(self):
        guard = _guard(max_position_pct=0.10)
        # Buying 100 shares @ $200 = $20k on a $100k portfolio = 20% → exceeds 10%
        result = guard.check_buy("AAPL", 100, 200.0, 100_000, [], 0.0)
        assert result.allowed is True
        assert result.adjusted_qty is not None
        assert result.adjusted_qty < 100
        assert result.adjusted_qty * 200 <= 10_000 + 1  # ≤ 10% of 100k

    def test_position_size_blocks_when_already_full(self):
        guard = _guard(max_position_pct=0.10)
        existing = _pos("AAPL", market_value=10_000)  # already at 10%
        result = guard.check_buy("AAPL", 10, 150.0, 100_000, [existing], 0.0)
        assert result.allowed is False

    def test_result_has_adjusted_qty_on_approval(self):
        guard = _guard()
        result = guard.check_buy("SPY", 5, 400.0, 100_000, [], 0.0)
        assert result.allowed is True
        assert result.adjusted_qty == 5


# ── check_stop_loss ───────────────────────────────────────────────────────────

class TestCheckStopLoss:
    def test_triggered_at_threshold(self):
        guard = _guard(stop_loss_pct=0.05)
        result = guard.check_stop_loss("AAPL", entry_price=100.0, current_price=94.0)
        assert result.allowed is False
        assert "Stop-loss" in result.reason

    def test_not_triggered_within_threshold(self):
        guard = _guard(stop_loss_pct=0.05)
        result = guard.check_stop_loss("AAPL", entry_price=100.0, current_price=97.0)
        assert result.allowed is True

    def test_exactly_at_threshold(self):
        guard = _guard(stop_loss_pct=0.05)
        result = guard.check_stop_loss("AAPL", entry_price=100.0, current_price=95.0)
        assert result.allowed is False  # >= threshold

    def test_zero_entry_price_is_safe(self):
        guard = _guard()
        result = guard.check_stop_loss("AAPL", entry_price=0.0, current_price=50.0)
        assert result.allowed is True

    def test_price_increase_never_triggers(self):
        guard = _guard(stop_loss_pct=0.05)
        result = guard.check_stop_loss("AAPL", entry_price=100.0, current_price=110.0)
        assert result.allowed is True


# ── scan_positions_for_stop_loss ─────────────────────────────────────────────

class TestScanPositions:
    def test_returns_breached_positions(self):
        guard = _guard(stop_loss_pct=0.05)
        positions = [
            _pos("AAPL", entry=100.0, current=93.0),  # -7% → triggered
            _pos("SPY",  entry=400.0, current=398.0), # -0.5% → safe
            _pos("GLD",  entry=180.0, current=170.0), # -5.6% → triggered
        ]
        to_close = guard.scan_positions_for_stop_loss(positions)
        tickers = [p["symbol"] for p in to_close]
        assert "AAPL" in tickers
        assert "GLD"  in tickers
        assert "SPY"  not in tickers

    def test_empty_positions(self):
        guard = _guard()
        assert guard.scan_positions_for_stop_loss([]) == []


# ── check_sell ────────────────────────────────────────────────────────────────

class TestCheckSell:
    def test_sell_within_held_qty(self):
        guard = _guard()
        positions = [_pos("AAPL", qty=50)]
        result = guard.check_sell("AAPL", 30, positions)
        assert result.allowed is True
        assert result.adjusted_qty == 30

    def test_sell_more_than_held_reduces_qty(self):
        guard = _guard()
        positions = [_pos("AAPL", qty=20)]
        result = guard.check_sell("AAPL", 50, positions)
        assert result.allowed is True
        assert result.adjusted_qty == 20

    def test_sell_symbol_not_held(self):
        guard = _guard()
        result = guard.check_sell("MSFT", 10, [])
        assert result.allowed is True
        assert result.adjusted_qty == 0
