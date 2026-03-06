"""Analysis pipeline — orchestrates indicators, sentiment, and geo risk.

Sprint 2 placeholder: each sub-module will be filled in Sprint 2.
"""

import structlog
from config import TRACKED_SYMBOLS

log = structlog.get_logger()


def run_analysis_pipeline() -> None:
    """Run full analysis for all tracked symbols and persist scores."""
    for ticker in TRACKED_SYMBOLS:
        try:
            _analyze_symbol(ticker)
        except Exception as exc:
            log.error("analysis.symbol_failed", ticker=ticker, error=str(exc))


def _analyze_symbol(ticker: str) -> None:
    log.info("analysis.symbol_start", ticker=ticker)
    # Sprint 2 modules (stubs until Sprint 2):
    # from analysis.indicators import compute_technical_score
    # from analysis.sentiment import compute_sentiment_score
    # from analysis.geo_risk import compute_geo_risk_score
    # technical = compute_technical_score(ticker)
    # sentiment = compute_sentiment_score(ticker)
    # geo_risk  = compute_geo_risk_score(ticker)
    # _persist_scores(ticker, technical, sentiment, geo_risk)
    log.info("analysis.symbol_done", ticker=ticker)
