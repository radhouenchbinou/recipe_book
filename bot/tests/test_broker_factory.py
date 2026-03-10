"""Tests for broker factory."""

import pytest
from unittest.mock import patch, MagicMock


class TestBrokerFactory:
    def test_returns_alpaca_by_default(self):
        with patch.dict("os.environ", {"BROKER": "alpaca"}), \
             patch("broker.alpaca.AlpacaBroker.__init__", return_value=None) as mock_init:
            from broker.factory import get_broker
            broker = get_broker()
            from broker.alpaca import AlpacaBroker
            assert isinstance(broker, AlpacaBroker)

    def test_explicit_alpaca(self):
        with patch("broker.alpaca.AlpacaBroker.__init__", return_value=None):
            from broker.factory import get_broker
            from broker.alpaca import AlpacaBroker
            broker = get_broker("alpaca")
            assert isinstance(broker, AlpacaBroker)

    def test_unknown_broker_raises(self):
        from broker.factory import get_broker
        with pytest.raises(ValueError, match="Unknown broker type"):
            get_broker("binance")

    def test_env_var_selects_broker(self):
        with patch.dict("os.environ", {"BROKER": "alpaca"}), \
             patch("broker.alpaca.AlpacaBroker.__init__", return_value=None):
            import importlib
            from broker import factory as f
            importlib.reload(f)
            from broker.factory import get_broker
            from broker.alpaca import AlpacaBroker
            assert isinstance(get_broker(), AlpacaBroker)
