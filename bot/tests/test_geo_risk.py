"""Unit tests for the geopolitical risk scorer.

Task S2-T3-001 acceptance criteria.
"""

from unittest.mock import MagicMock, patch

from analysis.geo_risk import (
    detect_events,
    _aggregate_events,
    GEO_RISK_EVENTS,
    SYMBOL_SENSITIVITY,
)


# ── Event detection ────────────────────────────────────────────────────────

def test_detect_war_event():
    events = detect_events("NATO allies respond to military invasion with troops deployed")
    names = [e.name for e, _ in events]
    assert "war_conflict" in names


def test_detect_sanctions():
    events = detect_events("US imposes sanctions and trade ban on exports")
    names = [e.name for e, _ in events]
    assert "sanctions" in names


def test_detect_no_events():
    events = detect_events("The weather today is sunny and mild")
    assert events == []


def test_detect_multiple_events():
    text = "War breaks out as recession fears mount amid new sanctions"
    events = detect_events(text)
    assert len(events) >= 2


# ── Score aggregation ──────────────────────────────────────────────────────

def test_aggregate_empty():
    assert _aggregate_events([]) == 0.0


def test_aggregate_single():
    event = GEO_RISK_EVENTS[0]  # war_conflict, base 90
    score = _aggregate_events([(event, 1.0)])
    assert score == 90.0


def test_aggregate_diminishing_returns():
    war = next(e for e in GEO_RISK_EVENTS if e.name == "war_conflict")
    sanctions = next(e for e in GEO_RISK_EVENTS if e.name == "sanctions")
    single = _aggregate_events([(war, 1.0)])
    combined = _aggregate_events([(war, 1.0), (sanctions, 1.0)])
    assert combined > single
    assert combined < single + sanctions.base_score  # diminishing returns


def test_aggregate_capped_at_100():
    score = _aggregate_events([(e, 1.0) for e in GEO_RISK_EVENTS])
    assert score <= 100.0


# ── Symbol sensitivity ─────────────────────────────────────────────────────

def test_gold_higher_sensitivity():
    assert SYMBOL_SENSITIVITY["GLD"] > SYMBOL_SENSITIVITY["SPY"]


# ── compute_geo_risk_score integration ────────────────────────────────────

@patch("analysis.geo_risk.get_session")
def test_compute_geo_risk_no_news(mock_session):
    session = MagicMock()
    session.execute.return_value.fetchall.return_value = []
    mock_session.return_value = session

    from analysis.geo_risk import compute_geo_risk_score
    result = compute_geo_risk_score("SPY")
    assert result.raw_score == 0.0
    assert result.adjusted_score == 0.0
    assert result.triggered_events == []


@patch("analysis.geo_risk.get_session")
def test_compute_geo_risk_with_war_news(mock_session):
    session = MagicMock()
    session.execute.return_value.fetchall.return_value = [
        ("NATO allies respond to military invasion", "Troops deployed along the border"),
        ("US imposes sanctions on imports", None),
    ]
    mock_session.return_value = session

    from analysis.geo_risk import compute_geo_risk_score
    result = compute_geo_risk_score("GLD")
    assert result.raw_score > 0.0
    assert result.adjusted_score >= result.raw_score  # GLD sensitivity > 1
    assert "war_conflict" in result.triggered_events


# ── Pipeline composite score ───────────────────────────────────────────────

def test_compute_composite_neutral():
    from analysis.pipeline import compute_composite_score
    score = compute_composite_score(technical=50.0, sentiment=0.0, geo_risk=0.0)
    assert 45.0 <= score <= 75.0


def test_compute_composite_bullish():
    from analysis.pipeline import compute_composite_score
    score = compute_composite_score(technical=80.0, sentiment=0.8, geo_risk=5.0)
    assert score > 70.0


def test_compute_composite_bearish():
    from analysis.pipeline import compute_composite_score
    score = compute_composite_score(technical=20.0, sentiment=-0.8, geo_risk=85.0)
    assert score < 30.0


def test_composite_always_in_range():
    from analysis.pipeline import compute_composite_score
    import random
    random.seed(0)
    for _ in range(100):
        score = compute_composite_score(
            technical=random.uniform(0, 100),
            sentiment=random.uniform(-1, 1),
            geo_risk=random.uniform(0, 100),
        )
        assert 0.0 <= score <= 100.0
