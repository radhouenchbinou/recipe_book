"""Tests for bot/alerts/engine.py — Phase 3 Sprint 1"""

import pytest
from unittest.mock import MagicMock, patch, call

from alerts.engine import AlertEngine, AlertFiring


# ── Fixtures ────────────────────────────────────────────────────────────────

def _engine(webhook=None, cooldown=60) -> AlertEngine:
    return AlertEngine(webhook=webhook, cooldown_minutes=cooldown)


def _alert(id=1, name="Test", condition="price_above", threshold=150.0, ticker="AAPL") -> dict:
    return {"id": id, "name": name, "condition": condition,
            "threshold": threshold, "ticker": ticker}


# ── run() ─────────────────────────────────────────────────────────────────────

class TestAlertEngineRun:
    @patch.object(AlertEngine, "_load_alerts", return_value=[])
    def test_no_alerts_returns_empty(self, _):
        engine = _engine()
        result = engine.run()
        assert result == []

    @patch.object(AlertEngine, "_record_firing")
    @patch.object(AlertEngine, "_fetch_current_value", return_value=160.0)
    @patch.object(AlertEngine, "_load_alerts")
    def test_price_above_fires_when_breached(self, mock_load, mock_fetch, mock_record):
        mock_load.return_value = [_alert(condition="price_above", threshold=150.0)]
        engine = _engine()
        firings = engine.run()
        assert len(firings) == 1
        assert firings[0].condition == "price_above"
        assert firings[0].current_value == 160.0

    @patch.object(AlertEngine, "_record_firing")
    @patch.object(AlertEngine, "_fetch_current_value", return_value=140.0)
    @patch.object(AlertEngine, "_load_alerts")
    def test_price_above_does_not_fire_when_below(self, mock_load, mock_fetch, mock_record):
        mock_load.return_value = [_alert(condition="price_above", threshold=150.0)]
        engine = _engine()
        firings = engine.run()
        assert len(firings) == 0

    @patch.object(AlertEngine, "_record_firing")
    @patch.object(AlertEngine, "_fetch_current_value", return_value=130.0)
    @patch.object(AlertEngine, "_load_alerts")
    def test_price_below_fires(self, mock_load, mock_fetch, mock_record):
        mock_load.return_value = [_alert(condition="price_below", threshold=140.0)]
        engine = _engine()
        firings = engine.run()
        assert len(firings) == 1
        assert firings[0].condition == "price_below"

    @patch.object(AlertEngine, "_record_firing")
    @patch.object(AlertEngine, "_fetch_current_value", return_value=72.0)
    @patch.object(AlertEngine, "_load_alerts")
    def test_score_above_fires(self, mock_load, mock_fetch, mock_record):
        mock_load.return_value = [_alert(condition="score_above", threshold=70.0)]
        engine = _engine()
        firings = engine.run()
        assert len(firings) == 1

    @patch.object(AlertEngine, "_record_firing")
    @patch.object(AlertEngine, "_fetch_current_value", return_value=35.0)
    @patch.object(AlertEngine, "_load_alerts")
    def test_score_below_fires(self, mock_load, mock_fetch, mock_record):
        mock_load.return_value = [_alert(condition="score_below", threshold=40.0)]
        engine = _engine()
        firings = engine.run()
        assert len(firings) == 1

    @patch.object(AlertEngine, "_record_firing")
    @patch.object(AlertEngine, "_fetch_current_value", return_value=6.5)
    @patch.object(AlertEngine, "_load_alerts")
    def test_change_pct_fires_on_large_move(self, mock_load, mock_fetch, mock_record):
        mock_load.return_value = [_alert(condition="change_pct", threshold=5.0)]
        engine = _engine()
        firings = engine.run()
        assert len(firings) == 1

    @patch.object(AlertEngine, "_record_firing")
    @patch.object(AlertEngine, "_fetch_current_value", return_value=None)
    @patch.object(AlertEngine, "_load_alerts")
    def test_no_data_does_not_fire(self, mock_load, mock_fetch, mock_record):
        mock_load.return_value = [_alert()]
        engine = _engine()
        firings = engine.run()
        assert len(firings) == 0
        mock_record.assert_not_called()

    @patch.object(AlertEngine, "_record_firing")
    @patch.object(AlertEngine, "_fetch_current_value", return_value=160.0)
    @patch.object(AlertEngine, "_load_alerts")
    def test_webhook_called_on_firing(self, mock_load, mock_fetch, mock_record):
        webhook = MagicMock()
        mock_load.return_value = [_alert(condition="price_above", threshold=150.0)]
        engine = _engine(webhook=webhook)
        engine.run()
        webhook.assert_called_once()
        payload = webhook.call_args[0][0]
        assert payload["ticker"] == "AAPL"
        assert payload["condition"] == "price_above"

    @patch.object(AlertEngine, "_record_firing")
    @patch.object(AlertEngine, "_fetch_current_value", return_value=160.0)
    @patch.object(AlertEngine, "_load_alerts")
    def test_webhook_error_does_not_crash_engine(self, mock_load, mock_fetch, mock_record):
        def bad_webhook(_):
            raise RuntimeError("webhook failed")
        mock_load.return_value = [_alert(condition="price_above", threshold=150.0)]
        engine = _engine(webhook=bad_webhook)
        firings = engine.run()   # must not raise
        assert len(firings) == 1

    @patch.object(AlertEngine, "_record_firing")
    @patch.object(AlertEngine, "_fetch_current_value", return_value=160.0)
    @patch.object(AlertEngine, "_load_alerts")
    def test_record_firing_called_on_breach(self, mock_load, mock_fetch, mock_record):
        alert = _alert(id=42, condition="price_above", threshold=150.0)
        mock_load.return_value = [alert]
        engine = _engine()
        engine.run()
        mock_record.assert_called_once_with(42, 160.0)


# ── AlertFiring dataclass ──────────────────────────────────────────────────

class TestAlertFiring:
    def test_fields_set_correctly(self):
        firing = AlertFiring(
            alert_id=1, name="Test", ticker="AAPL",
            condition="price_above", threshold=150.0,
            current_value=165.0, message="fired",
        )
        assert firing.alert_id == 1
        assert firing.ticker == "AAPL"
        assert firing.current_value == 165.0

    def test_payload_helper(self):
        firing = AlertFiring(
            alert_id=5, name="Score Alert", ticker="SPY",
            condition="score_above", threshold=70.0,
            current_value=75.0, message="ok",
        )
        payload = AlertEngine._payload(firing)
        assert payload["ticker"] == "SPY"
        assert payload["threshold"] == 70.0
        assert payload["current_value"] == 75.0
