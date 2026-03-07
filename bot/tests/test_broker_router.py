"""Tests for bot/broker/router.py — Phase 3 Sprint 2"""

import pytest
from unittest.mock import patch, MagicMock

from broker.router import get_broker, SimBroker
from broker.base import BaseBroker, OrderResult


# ── SimBroker unit tests ─────────────────────────────────────────────────────

class TestSimBroker:
    def test_is_paper(self):
        assert SimBroker().is_paper is True

    def test_name(self):
        assert SimBroker().name == "sim"

    def test_is_market_open(self):
        assert SimBroker().is_market_open() is True

    def test_healthcheck(self):
        assert SimBroker().healthcheck() is True

    def test_initial_account(self):
        broker = SimBroker()
        acct = broker.get_account()
        assert acct["cash"] == 100_000.0
        assert acct["portfolio_value"] == 100_000.0
        assert acct["is_paper"] is True

    def test_buy_reduces_cash(self):
        broker = SimBroker(prices={"AAPL": 150.0})
        result = broker.place_market_order("AAPL", 10, "buy")
        assert result.status == "filled"
        assert result.filled_price == 150.0
        acct = broker.get_account()
        assert acct["cash"] == pytest.approx(100_000.0 - 1_500.0)

    def test_buy_creates_position(self):
        broker = SimBroker(prices={"AAPL": 100.0})
        broker.place_market_order("AAPL", 5, "buy")
        pos = broker.get_position("AAPL")
        assert pos is not None
        assert pos["qty"] == 5
        assert pos["avg_entry_price"] == 100.0

    def test_sell_increases_cash(self):
        broker = SimBroker(prices={"AAPL": 200.0})
        broker.place_market_order("AAPL", 10, "buy")
        cash_after_buy = broker.get_account()["cash"]
        broker.place_market_order("AAPL", 5, "sell")
        cash_after_sell = broker.get_account()["cash"]
        assert cash_after_sell > cash_after_buy

    def test_sell_removes_position_when_fully_sold(self):
        broker = SimBroker(prices={"AAPL": 100.0})
        broker.place_market_order("AAPL", 3, "buy")
        broker.place_market_order("AAPL", 3, "sell")
        assert broker.get_position("AAPL") is None

    def test_buy_rejected_on_insufficient_cash(self):
        broker = SimBroker(prices={"AAPL": 1_000.0})
        result = broker.place_market_order("AAPL", 200, "buy")  # $200k > $100k cash
        assert result.status == "rejected"
        assert result.error is not None

    def test_sell_rejected_on_insufficient_shares(self):
        broker = SimBroker(prices={"AAPL": 100.0})
        result = broker.place_market_order("AAPL", 5, "sell")  # no position
        assert result.status == "rejected"

    def test_qty_zero_rejected_on_buy(self):
        broker = SimBroker()
        result = broker.place_market_order("AAPL", 0, "buy")
        assert result.status == "rejected"

    def test_get_positions_empty(self):
        assert SimBroker().get_positions() == []

    def test_get_positions_after_buy(self):
        broker = SimBroker(prices={"SPY": 400.0})
        broker.place_market_order("SPY", 2, "buy")
        positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0]["symbol"] == "SPY"

    def test_cancel_order_returns_false(self):
        # sim orders fill immediately — nothing to cancel
        assert SimBroker().cancel_order("sim-0001") is False

    def test_average_entry_price_after_partial_fill(self):
        broker = SimBroker(prices={"TSLA": 100.0})
        broker.place_market_order("TSLA", 10, "buy")   # avg=100
        broker._prices["TSLA"] = 200.0
        broker.place_market_order("TSLA", 10, "buy")   # avg should be 150
        pos = broker.get_position("TSLA")
        assert pos["avg_entry_price"] == pytest.approx(150.0)

    def test_order_id_increments(self):
        broker = SimBroker(prices={"A": 10.0, "B": 10.0})
        r1 = broker.place_market_order("A", 1, "buy")
        r2 = broker.place_market_order("B", 1, "buy")
        assert r1.order_id != r2.order_id

    def test_default_price_when_symbol_unknown(self):
        broker = SimBroker()   # no price map
        result = broker.place_market_order("UNKNOWN", 1, "buy")
        assert result.status == "filled"
        assert result.filled_price == 100.0   # fallback default


# ── get_broker() factory ──────────────────────────────────────────────────────

class TestGetBroker:
    def test_sim_mode_returns_sim_broker(self):
        broker = get_broker(mode="sim")
        assert isinstance(broker, SimBroker)

    def test_paper_mode_returns_alpaca_broker(self):
        with patch("broker.router.AlpacaBroker") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.name = "alpaca-paper"
            mock_cls.return_value = mock_instance
            broker = get_broker(mode="paper")
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args.kwargs
        assert "paper" in call_kwargs["base_url"]

    def test_live_mode_returns_alpaca_broker(self):
        with patch("broker.router.AlpacaBroker") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.name = "alpaca-live"
            mock_cls.return_value = mock_instance
            broker = get_broker(mode="live")
        call_kwargs = mock_cls.call_args.kwargs
        assert "paper" not in call_kwargs["base_url"]

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown broker mode"):
            get_broker(mode="coinbase")

    def test_default_mode_is_paper(self):
        with patch("broker.router.AlpacaBroker") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            with patch.dict("os.environ", {}, clear=True):
                get_broker()
        # Should have called with paper URL (no explicit mode → env not set → "paper")
        call_kwargs = mock_cls.call_args.kwargs
        assert "paper" in call_kwargs["base_url"]

    def test_env_var_overrides_default(self):
        with patch("broker.router.AlpacaBroker") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            with patch.dict("os.environ", {"BROKER_MODE": "sim"}, clear=False):
                broker = get_broker()
        # When BROKER_MODE=sim, AlpacaBroker should not be called
        mock_cls.assert_not_called()

    def test_sim_is_base_broker_subclass(self):
        broker = get_broker(mode="sim")
        assert isinstance(broker, BaseBroker)
