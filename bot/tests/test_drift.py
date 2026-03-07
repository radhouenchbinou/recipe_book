"""Tests for bot/portfolio/drift.py — Phase 2 Sprint 3"""

import pytest

from portfolio.drift import DriftDetector, DriftReport, DriftEntry


# ── Fixtures ───────────────────────────────────────────────────────────────

def _detector(**kwargs) -> DriftDetector:
    return DriftDetector(
        drift_threshold=kwargs.get("drift_threshold", 0.03),
        min_order_value=kwargs.get("min_order_value", 500.0),
    )


def _pos(symbol, market_value=5000, qty=50, price=100.0) -> dict:
    return {"symbol": symbol, "market_value": market_value,
            "qty": qty, "current_price": price}


# ── detect ─────────────────────────────────────────────────────────────────

class TestDriftDetect:
    def test_returns_drift_report(self):
        detector = _detector()
        report = detector.detect(
            target_weights={"AAPL": 0.10, "SPY": 0.20},
            current_positions=[_pos("AAPL", market_value=10_000), _pos("SPY", market_value=15_000)],
            portfolio_value=100_000,
        )
        assert isinstance(report, DriftReport)
        assert len(report.entries) > 0

    def test_overweight_symbol_gets_sell_action(self):
        detector = _detector(drift_threshold=0.03)
        report = detector.detect(
            target_weights={"AAPL": 0.10},
            current_positions=[_pos("AAPL", market_value=20_000)],  # 20% actual vs 10% target
            portfolio_value=100_000,
        )
        aapl = next(e for e in report.entries if e.ticker == "AAPL")
        assert aapl.action == "sell"
        assert aapl.drift > 0

    def test_underweight_symbol_gets_buy_action(self):
        detector = _detector(drift_threshold=0.03)
        report = detector.detect(
            target_weights={"SPY": 0.20},
            current_positions=[_pos("SPY", market_value=5_000)],  # 5% actual vs 20% target
            portfolio_value=100_000,
        )
        spy = next(e for e in report.entries if e.ticker == "SPY")
        assert spy.action == "buy"
        assert spy.drift < 0

    def test_no_drift_gives_hold(self):
        detector = _detector(drift_threshold=0.03)
        report = detector.detect(
            target_weights={"AAPL": 0.10},
            current_positions=[_pos("AAPL", market_value=10_200)],  # 10.2% — within 3%
            portfolio_value=100_000,
        )
        aapl = next(e for e in report.entries if e.ticker == "AAPL")
        assert aapl.action == "hold"

    def test_zero_portfolio_value_no_crash(self):
        detector = _detector()
        report = detector.detect(
            target_weights={"AAPL": 0.10},
            current_positions=[],
            portfolio_value=0,
        )
        assert isinstance(report, DriftReport)

    def test_missing_position_treated_as_zero(self):
        detector = _detector(drift_threshold=0.03)
        # MSFT in target but no position
        report = detector.detect(
            target_weights={"MSFT": 0.15},
            current_positions=[],
            portfolio_value=100_000,
        )
        msft = next(e for e in report.entries if e.ticker == "MSFT")
        assert msft.current_weight == 0.0
        assert msft.action == "buy"

    def test_held_but_not_in_target_gets_sell(self):
        detector = _detector(drift_threshold=0.03)
        report = detector.detect(
            target_weights={},  # empty target
            current_positions=[_pos("AAPL", market_value=15_000)],
            portfolio_value=100_000,
        )
        aapl = next(e for e in report.entries if e.ticker == "AAPL")
        assert aapl.action == "sell"

    def test_micro_orders_suppressed(self):
        detector = _detector(drift_threshold=0.001, min_order_value=500.0)
        # 0.2% drift on $100k = $200 — below min_order_value
        report = detector.detect(
            target_weights={"AAPL": 0.10},
            current_positions=[_pos("AAPL", market_value=10_200)],
            portfolio_value=100_000,
        )
        aapl = next(e for e in report.entries if e.ticker == "AAPL")
        assert aapl.action == "hold"

    def test_needs_rebalance_flag(self):
        detector = _detector(drift_threshold=0.03)
        report = detector.detect(
            target_weights={"AAPL": 0.10},
            current_positions=[_pos("AAPL", market_value=20_000)],
            portfolio_value=100_000,
        )
        assert report.needs_rebalance is True

    def test_rebalance_count(self):
        detector = _detector(drift_threshold=0.03)
        report = detector.detect(
            target_weights={"AAPL": 0.10, "SPY": 0.20, "GLD": 0.05},
            current_positions=[
                _pos("AAPL", market_value=20_000),   # drift = +10%
                _pos("SPY",  market_value=20_000),   # drift = 0%
                _pos("GLD",  market_value=15_000),   # drift = +10%
            ],
            portfolio_value=100_000,
        )
        assert report.rebalance_count == 2


# ── to_orders ──────────────────────────────────────────────────────────────

class TestToOrders:
    def test_generates_orders_for_drifted_positions(self):
        detector = _detector(drift_threshold=0.03)
        report = detector.detect(
            target_weights={"AAPL": 0.10},
            current_positions=[_pos("AAPL", market_value=20_000)],
            portfolio_value=100_000,
        )
        orders = detector.to_orders(report, price_map={"AAPL": 150.0})
        assert len(orders) == 1
        assert orders[0]["symbol"] == "AAPL"
        assert orders[0]["action"] == "sell"
        assert orders[0]["qty"] >= 1

    def test_no_price_skips_order(self):
        detector = _detector(drift_threshold=0.03)
        report = detector.detect(
            target_weights={"AAPL": 0.10},
            current_positions=[_pos("AAPL", market_value=20_000)],
            portfolio_value=100_000,
        )
        orders = detector.to_orders(report, price_map={})   # no price for AAPL
        assert orders == []

    def test_hold_entries_excluded(self):
        detector = _detector(drift_threshold=0.03)
        report = detector.detect(
            target_weights={"AAPL": 0.10, "SPY": 0.20},
            current_positions=[
                _pos("AAPL", market_value=20_000),  # drifted → sell
                _pos("SPY",  market_value=20_000),  # on target → hold
            ],
            portfolio_value=100_000,
        )
        orders = detector.to_orders(report, price_map={"AAPL": 150.0, "SPY": 400.0})
        assert all(o["symbol"] != "SPY" for o in orders)
