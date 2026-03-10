"""Unit tests for the smart trigger.

Task S3-T1-003 acceptance criteria.
"""

from unittest.mock import patch
from claude.trigger import should_call_claude


@patch("claude.trigger.can_call_claude", return_value=True)
def test_call_approved_large_delta(mock_budget):
    ok, reason = should_call_claude("SPY", composite_score=72.0, previous_composite=55.0)
    assert ok is True
    assert reason == "score_actionable"


@patch("claude.trigger.can_call_claude", return_value=True)
def test_skip_small_delta(mock_budget):
    ok, reason = should_call_claude("SPY", composite_score=55.0, previous_composite=53.0)
    assert ok is False
    assert "delta_too_small" in reason


@patch("claude.trigger.can_call_claude", return_value=False)
def test_skip_budget_exhausted(mock_budget):
    ok, reason = should_call_claude("SPY", composite_score=80.0, previous_composite=50.0)
    assert ok is False
    assert reason == "budget_exhausted"


@patch("claude.trigger.can_call_claude", return_value=True)
def test_skip_neutral_band(mock_budget):
    ok, reason = should_call_claude("SPY", composite_score=50.0, previous_composite=None)
    assert ok is False
    assert reason == "solidly_neutral"


@patch("claude.trigger.can_call_claude", return_value=False)
def test_force_overrides_budget(mock_budget):
    ok, reason = should_call_claude("SPY", composite_score=50.0, previous_composite=50.0, force=True)
    assert ok is True
    assert reason == "forced"


@patch("claude.trigger.can_call_claude", return_value=True)
def test_no_previous_score_still_triggers(mock_budget):
    # No delta check when no previous score exists and score is actionable
    ok, reason = should_call_claude("SPY", composite_score=80.0, previous_composite=None)
    assert ok is True
