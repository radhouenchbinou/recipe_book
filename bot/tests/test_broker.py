"""Unit tests for the Alpaca broker connector.

Task S1-T3-001 acceptance criteria.
"""

from unittest.mock import MagicMock, patch
import pytest


@patch("broker.connector.tradeapi.REST")
def test_get_account(mock_rest):
    acct = MagicMock()
    acct.id = "abc123"
    acct.equity = "100000.00"
    acct.cash = "50000.00"
    acct.buying_power = "80000.00"
    acct.portfolio_value = "100000.00"
    acct.status = "ACTIVE"
    mock_rest.return_value.get_account.return_value = acct

    from broker.connector import BrokerConnector
    bc = BrokerConnector(api_key="k", secret_key="s", base_url="https://paper-api.alpaca.markets")
    info = bc.get_account()

    assert info.account_id == "abc123"
    assert info.equity == 100_000.0
    assert info.is_paper is True


@patch("broker.connector.tradeapi.REST")
def test_get_positions(mock_rest):
    pos = MagicMock()
    pos.symbol = "AAPL"
    pos.qty = "10"
    pos.market_value = "1850.00"
    pos.unrealized_pl = "50.00"
    pos.current_price = "185.00"
    mock_rest.return_value.list_positions.return_value = [pos]

    from broker.connector import BrokerConnector
    bc = BrokerConnector(api_key="k", secret_key="s", base_url="https://paper-api.alpaca.markets")
    positions = bc.get_positions()

    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].qty == 10.0


@patch("broker.connector.tradeapi.REST")
def test_place_market_order_invalid_side(mock_rest):
    from broker.connector import BrokerConnector
    bc = BrokerConnector(api_key="k", secret_key="s", base_url="https://paper-api.alpaca.markets")

    with pytest.raises(ValueError, match="Invalid side"):
        bc.place_market_order("AAPL", 5, "hold")


@patch("broker.connector.tradeapi.REST")
def test_healthcheck_success(mock_rest):
    mock_rest.return_value.get_account.return_value = MagicMock()
    from broker.connector import BrokerConnector
    bc = BrokerConnector(api_key="k", secret_key="s", base_url="https://paper-api.alpaca.markets")
    assert bc.healthcheck() is True
