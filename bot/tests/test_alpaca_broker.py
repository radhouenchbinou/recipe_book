"""Tests for bot/broker/alpaca.py — Phase 3 Sprint 2"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from broker.alpaca import AlpacaBroker
from broker.base import OrderResult


def _make_broker(base_url="https://paper-api.alpaca.markets"):
    with patch("broker.alpaca.tradeapi.REST"):
        broker = AlpacaBroker(api_key="key", secret_key="secret", base_url=base_url)
    return broker


class TestAlpacaBrokerProperties:
    def test_is_paper_true_for_paper_url(self):
        broker = _make_broker("https://paper-api.alpaca.markets")
        assert broker.is_paper is True

    def test_is_paper_false_for_live_url(self):
        broker = _make_broker("https://api.alpaca.markets")
        assert broker.is_paper is False

    def test_name_paper(self):
        assert _make_broker("https://paper-api.alpaca.markets").name == "alpaca-paper"

    def test_name_live(self):
        assert _make_broker("https://api.alpaca.markets").name == "alpaca-live"


class TestAlpacaBrokerAccount:
    def test_get_account_returns_dict(self):
        broker = _make_broker()
        mock_acct = MagicMock()
        mock_acct.portfolio_value = "10000"
        mock_acct.cash            = "5000"
        mock_acct.equity          = "10000"
        mock_acct.unrealized_pl   = "100"
        mock_acct.buying_power    = "5000"
        broker._api.get_account.return_value = mock_acct

        result = broker.get_account()
        assert result["portfolio_value"] == 10000.0
        assert result["cash"]            == 5000.0
        assert result["is_paper"]        is True

    def test_get_positions_returns_list(self):
        broker = _make_broker()
        mock_pos = MagicMock()
        mock_pos.symbol          = "AAPL"
        mock_pos.qty             = "10"
        mock_pos.market_value    = "1500"
        mock_pos.current_price   = "150"
        mock_pos.avg_entry_price = "140"
        mock_pos.unrealized_pl   = "100"
        broker._api.list_positions.return_value = [mock_pos]

        positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0]["symbol"] == "AAPL"
        assert positions[0]["qty"]    == 10.0

    def test_get_position_returns_none_on_error(self):
        broker = _make_broker()
        broker._api.get_position.side_effect = Exception("not found")
        result = broker.get_position("AAPL")
        assert result is None


class TestAlpacaBrokerOrders:
    def test_place_market_order_success(self):
        broker = _make_broker()
        mock_order = MagicMock()
        mock_order.id     = "abc-123"
        mock_order.status = "accepted"
        broker._api.submit_order.return_value = mock_order

        result = broker.place_market_order("AAPL", 10, "buy")
        assert isinstance(result, OrderResult)
        assert result.order_id == "abc-123"
        assert result.status   == "accepted"
        assert result.error    is None

    def test_place_market_order_rejected_on_zero_qty(self):
        broker = _make_broker()
        result = broker.place_market_order("AAPL", 0, "buy")
        assert result.status == "rejected"
        assert "qty" in result.error

    def test_place_market_order_rejected_on_api_error(self):
        broker = _make_broker()
        broker._api.submit_order.side_effect = Exception("API error")
        result = broker.place_market_order("AAPL", 5, "buy")
        assert result.status == "rejected"
        assert result.error is not None

    def test_cancel_order_true_on_success(self):
        broker = _make_broker()
        broker._api.cancel_order.return_value = None
        assert broker.cancel_order("order-1") is True

    def test_cancel_order_false_on_error(self):
        broker = _make_broker()
        broker._api.cancel_order.side_effect = Exception("not found")
        assert broker.cancel_order("order-1") is False


class TestAlpacaBrokerMarketStatus:
    def test_is_market_open_true(self):
        broker = _make_broker()
        clock = MagicMock()
        clock.is_open = True
        broker._api.get_clock.return_value = clock
        assert broker.is_market_open() is True

    def test_is_market_open_false_on_error(self):
        broker = _make_broker()
        broker._api.get_clock.side_effect = Exception("network error")
        assert broker.is_market_open() is False

    def test_healthcheck_true(self):
        broker = _make_broker()
        broker._api.get_account.return_value = MagicMock()
        assert broker.healthcheck() is True

    def test_healthcheck_false_on_error(self):
        broker = _make_broker()
        broker._api.get_account.side_effect = Exception("unreachable")
        assert broker.healthcheck() is False
