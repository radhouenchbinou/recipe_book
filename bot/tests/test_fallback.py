"""Unit tests for the fallback rule-based recommender.

Task S3-T2-003 acceptance criteria.
"""

import pytest
from claude.fallback import generate_fallback_recommendation


def _rec(composite, technical=50.0, geo_risk=10.0, sentiment=None):
    return generate_fallback_recommendation(
        ticker="SPY",
        composite_score=composite,
        technical_score=technical,
        geo_risk_score=geo_risk,
        sentiment_score=sentiment,
    )


# ── Action thresholds ──────────────────────────────────────────────────────

def test_strong_bullish_gives_buy():
    rec = _rec(composite=70.0)
    assert rec.action == "buy"
    assert rec.source == "fallback"


def test_strong_bearish_gives_sell():
    rec = _rec(composite=30.0)
    assert rec.action == "sell"


def test_neutral_gives_hold():
    rec = _rec(composite=50.0)
    assert rec.action == "hold"


def test_boundary_at_65_is_buy():
    rec = _rec(composite=65.0)
    assert rec.action == "buy"


def test_boundary_at_35_is_sell():
    rec = _rec(composite=35.0)
    assert rec.action == "sell"


def test_boundary_just_above_35_is_hold():
    rec = _rec(composite=36.0)
    assert rec.action == "hold"


# ── Confidence scaling ─────────────────────────────────────────────────────

def test_high_composite_higher_confidence():
    rec_high = _rec(composite=90.0)
    rec_mid  = _rec(composite=66.0)
    assert rec_high.confidence > rec_mid.confidence


def test_confidence_always_in_range():
    for score in [0, 10, 35, 50, 65, 90, 100]:
        rec = _rec(composite=float(score))
        assert 0.0 <= rec.confidence <= 1.0


# ── Risk flags ─────────────────────────────────────────────────────────────

def test_high_geo_risk_appears_in_risks():
    rec = _rec(composite=70.0, geo_risk=75.0)
    assert any("geopolitical" in r.lower() for r in rec.key_risks)


def test_negative_sentiment_appears_in_risks():
    rec = _rec(composite=70.0, sentiment=-0.5)
    assert any("sentiment" in r.lower() for r in rec.key_risks)


# ── Position sizing ────────────────────────────────────────────────────────

def test_sell_has_zero_position():
    rec = _rec(composite=20.0)
    assert rec.suggested_position_size == 0.0


def test_buy_position_within_limits():
    rec = _rec(composite=75.0)
    assert 0.0 < rec.suggested_position_size <= 0.10


# ── Source tag ─────────────────────────────────────────────────────────────

def test_source_is_fallback():
    for score in [20.0, 50.0, 80.0]:
        rec = _rec(composite=score)
        assert rec.source == "fallback"
