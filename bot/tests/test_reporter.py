"""Tests for bot/reporting/reporter.py — Phase 3 Sprint 2"""

import pytest
from unittest.mock import MagicMock, patch

from reporting.reporter import Reporter, Report, TradeRow, PnlRow, AccuracyRow


# ── Fixtures / helpers ───────────────────────────────────────────────────────

def _make_trade_row(**kwargs):
    defaults = dict(
        id=1, order_id="ord-001", broker="alpaca-paper",
        symbol="AAPL", side="buy", qty=10, status="filled",
        filled_price=150.0, error=None, source="rebalance",
        created_at="2026-03-01T12:00:00",
    )
    defaults.update(kwargs)
    return TradeRow(**defaults)


def _mock_session(rows):
    """Return a mock get_session() context that yields the given rows."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = rows
    mock_sess = MagicMock()
    mock_sess.execute.return_value = mock_result
    return mock_sess


# ── Reporter.trade_log ───────────────────────────────────────────────────────

class TestTradeLog:
    @patch("reporting.reporter.get_session")
    def test_returns_report_object(self, mock_get):
        mock_get.return_value = _mock_session([])
        reporter = Reporter()
        report = reporter.trade_log()
        assert isinstance(report, Report)
        assert report.report_type == "trade_log"

    @patch("reporting.reporter.get_session")
    def test_empty_db_returns_empty_rows(self, mock_get):
        mock_get.return_value = _mock_session([])
        report = Reporter().trade_log()
        assert report.rows == []
        assert report.summary["total_orders"] == 0

    @patch("reporting.reporter.get_session")
    def test_rows_mapped_correctly(self, mock_get):
        raw_row = (1, "ord-001", "alpaca-paper", "AAPL", "buy",
                   10, "filled", 150.0, None, "rebalance", "2026-03-01")
        mock_get.return_value = _mock_session([raw_row])
        report = Reporter().trade_log()
        assert len(report.rows) == 1
        row = report.rows[0]
        assert row["symbol"] == "AAPL"
        assert row["side"]   == "buy"
        assert row["qty"]    == 10

    @patch("reporting.reporter.get_session")
    def test_summary_counts_buys_sells(self, mock_get):
        rows = [
            (1, "o1", "alpaca-paper", "AAPL", "buy",  5, "filled", 100.0, None, None, "2026-03-01"),
            (2, "o2", "alpaca-paper", "AAPL", "sell", 3, "filled", 110.0, None, None, "2026-03-02"),
            (3, "o3", "alpaca-paper", "SPY",  "buy",  2, "rejected", None, "err", None, "2026-03-03"),
        ]
        mock_get.return_value = _mock_session(rows)
        report = Reporter().trade_log()
        assert report.summary["filled_buys"]  == 1
        assert report.summary["filled_sells"] == 1
        assert report.summary["total_orders"] == 3

    @patch("reporting.reporter.get_session")
    def test_filters_stored_in_report(self, mock_get):
        mock_get.return_value = _mock_session([])
        report = Reporter().trade_log(symbol="TSLA", days=7)
        assert report.filters["symbol"] == "TSLA"
        assert report.filters["days"]   == 7


# ── Reporter.pnl_summary ─────────────────────────────────────────────────────

class TestPnlSummary:
    @patch("reporting.reporter.get_session")
    def test_returns_report_object(self, mock_get):
        mock_get.return_value = _mock_session([])
        report = Reporter().pnl_summary()
        assert report.report_type == "pnl_summary"

    @patch("reporting.reporter.get_session")
    def test_basic_pnl_calculation(self, mock_get):
        # bought 10 @ $100, sold 10 @ $120 → realised P&L = $200
        rows = [
            ("AAPL", "buy",  10, 100.0),
            ("AAPL", "sell", 10, 120.0),
        ]
        mock_get.return_value = _mock_session(rows)
        report = Reporter().pnl_summary()
        assert len(report.rows) == 1
        assert report.rows[0]["realised_pl"] == pytest.approx(200.0)
        assert report.summary["total_realised_pl"] == pytest.approx(200.0)

    @patch("reporting.reporter.get_session")
    def test_loss_scenario(self, mock_get):
        rows = [
            ("SPY", "buy",  5, 400.0),
            ("SPY", "sell", 5, 350.0),
        ]
        mock_get.return_value = _mock_session(rows)
        report = Reporter().pnl_summary()
        assert report.rows[0]["realised_pl"] == pytest.approx(-250.0)

    @patch("reporting.reporter.get_session")
    def test_multiple_symbols(self, mock_get):
        rows = [
            ("AAPL", "buy",  10, 100.0),
            ("AAPL", "sell", 10, 110.0),
            ("TSLA", "buy",   5, 200.0),
            ("TSLA", "sell",  5, 180.0),
        ]
        mock_get.return_value = _mock_session(rows)
        report = Reporter().pnl_summary()
        symbols = {r["symbol"] for r in report.rows}
        assert "AAPL" in symbols
        assert "TSLA" in symbols

    @patch("reporting.reporter.get_session")
    def test_rows_sorted_by_pnl_desc(self, mock_get):
        rows = [
            ("LOW", "buy", 1, 100.0), ("LOW", "sell", 1, 90.0),   # -10
            ("HIGH", "buy", 1, 100.0), ("HIGH", "sell", 1, 150.0), # +50
        ]
        mock_get.return_value = _mock_session(rows)
        report = Reporter().pnl_summary()
        assert report.rows[0]["realised_pl"] > report.rows[-1]["realised_pl"]


# ── Reporter.recommendation_accuracy ─────────────────────────────────────────

class TestRecommendationAccuracy:
    @patch("reporting.reporter.get_session")
    def test_returns_report_object(self, mock_get):
        mock_get.return_value = _mock_session([])
        report = Reporter().recommendation_accuracy()
        assert report.report_type == "recommendation_accuracy"

    @patch("reporting.reporter.get_session")
    def test_pct_followed_calculation(self, mock_get):
        rows = [("claude", "buy", 10, 4)]   # 4 of 10 followed → 40%
        mock_get.return_value = _mock_session(rows)
        report = Reporter().recommendation_accuracy()
        assert report.rows[0]["pct_followed"] == pytest.approx(40.0)

    @patch("reporting.reporter.get_session")
    def test_zero_total_does_not_divide_by_zero(self, mock_get):
        rows = [("fallback", "hold", 0, 0)]
        mock_get.return_value = _mock_session(rows)
        report = Reporter().recommendation_accuracy()
        assert report.rows[0]["pct_followed"] == 0.0


# ── Export helpers ────────────────────────────────────────────────────────────

class TestExportHelpers:
    def _sample_report(self):
        return Report(
            report_type="trade_log",
            generated_at="2026-03-07T00:00:00",
            filters={"days": 30},
            rows=[{"symbol": "AAPL", "side": "buy", "qty": 10}],
            summary={"total_orders": 1},
        )

    def test_to_json_returns_string(self):
        report = self._sample_report()
        result = Reporter.to_json(report)
        assert isinstance(result, str)
        assert "AAPL" in result

    def test_to_json_is_valid_json(self):
        import json
        report = self._sample_report()
        parsed = json.loads(Reporter.to_json(report))
        assert parsed["report_type"] == "trade_log"
        assert len(parsed["rows"]) == 1

    def test_to_csv_returns_string(self):
        report = self._sample_report()
        result = Reporter.to_csv(report)
        assert isinstance(result, str)
        assert "symbol" in result   # header row
        assert "AAPL" in result

    def test_to_csv_empty_rows_returns_empty_string(self):
        report = Report(
            report_type="trade_log",
            generated_at="2026-03-07T00:00:00",
            filters={},
            rows=[],
            summary={},
        )
        assert Reporter.to_csv(report) == ""

    def test_to_csv_has_header_row(self):
        report = self._sample_report()
        csv_str = Reporter.to_csv(report)
        lines = csv_str.strip().split("\n")
        assert lines[0].startswith("symbol") or "symbol" in lines[0]
        assert len(lines) == 2   # header + 1 data row
