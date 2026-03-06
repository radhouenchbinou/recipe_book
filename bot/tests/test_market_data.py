"""Unit tests for the market data collector.

Task S1-T2-001 acceptance criteria.
"""

from datetime import date
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest


@pytest.fixture()
def sample_ohlcv():
    idx = pd.DatetimeIndex([pd.Timestamp("2024-01-10")])
    return pd.DataFrame(
        {"Open": [480.0], "High": [485.0], "Low": [478.0], "Close": [483.5], "Volume": [90_000_000]},
        index=idx,
    )


@patch("collectors.market_data.get_session")
@patch("collectors.market_data.yf.download")
def test_fetch_symbol_saves_rows(mock_download, mock_session, sample_ohlcv):
    mock_download.return_value = sample_ohlcv

    session = MagicMock()
    mock_session.return_value = session

    from collectors.market_data import fetch_symbol

    count = fetch_symbol("SPY", start=date(2024, 1, 10), end=date(2024, 1, 10))

    assert count == 1
    session.commit.assert_called_once()


@patch("collectors.market_data.get_session")
@patch("collectors.market_data.yf.download")
def test_fetch_symbol_empty_returns_zero(mock_download, mock_session):
    mock_download.return_value = pd.DataFrame()
    session = MagicMock()
    mock_session.return_value = session

    from collectors.market_data import fetch_symbol

    count = fetch_symbol("SPY")
    assert count == 0
    session.commit.assert_not_called()


@patch("collectors.market_data.fetch_symbol")
def test_fetch_all_symbols(mock_fetch):
    mock_fetch.return_value = 3
    from collectors.market_data import fetch_all_symbols
    from config import TRACKED_SYMBOLS

    results = fetch_all_symbols()
    assert set(results.keys()) == set(TRACKED_SYMBOLS)
    assert all(v == 3 for v in results.values())
