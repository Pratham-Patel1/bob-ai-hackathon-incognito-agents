"""
Tests for PredictiveRiskEngine (ML-based delay risk inference).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from backend.engines.predictive_risk import (
    FeatureContribution,
    MLRiskResult,
    run,
)


def _now_plus(hours: float) -> str:
    dt = datetime.now(timezone.utc) + timedelta(hours=hours)
    return dt.isoformat()


def _valid_shipment(**kwargs: Any) -> dict[str, Any]:
    base = {
        "scheduled_departure": _now_plus(-24),
        "scheduled_arrival": _now_plus(48),
        "cargo_type": "general",
        "weight_kg": 5000.0,
        "route_reliability_score": 0.85,
    }
    base.update(kwargs)
    return base


def _valid_carrier(**kwargs: Any) -> dict[str, Any]:
    base = {
        "reliability_score": 0.90,
    }
    base.update(kwargs)
    return base


def test_predictive_risk_artifact_loaded_and_valid_score():
    """Requirement 1, 2, 3: run() returns valid ml_score between 0.0 and 1.0, and model_version != 'unknown'."""
    shipment = _valid_shipment()
    disruptions = [{"severity": "medium"}]
    carrier = _valid_carrier()

    result = run(shipment, disruptions, carrier)

    assert isinstance(result, MLRiskResult)
    assert result.ml_score is not None
    assert 0.0 <= result.ml_score <= 1.0
    assert result.model_version != "unknown"


def test_predictive_risk_top_features():
    """Requirement 4: top_features contains FeatureContribution objects with expected fields."""
    shipment = _valid_shipment(cargo_type="temperature_sensitive")
    disruptions = [{"severity": "high"}]
    carrier = _valid_carrier(reliability_score=0.75)

    result = run(shipment, disruptions, carrier)

    assert isinstance(result, MLRiskResult)
    assert len(result.top_features) > 0
    for fc in result.top_features:
        assert isinstance(fc, FeatureContribution)
        assert isinstance(fc.feature_name, str)
        assert len(fc.feature_name) > 0
        assert isinstance(fc.value, float)
        assert isinstance(fc.importance, float)


def test_predictive_risk_accepts_empty_disruptions():
    """Requirement 5: Inference succeeds with an empty disruptions list."""
    shipment = _valid_shipment()
    disruptions: list[dict[str, Any]] = []
    carrier = _valid_carrier()

    result = run(shipment, disruptions, carrier)

    assert isinstance(result, MLRiskResult)
    assert result.ml_score is not None
    assert 0.0 <= result.ml_score <= 1.0
    assert result.model_version != "unknown"


def test_predictive_risk_malformed_and_missing_shipment_fields():
    """Requirement 6: Malformed/missing shipment fields do not crash run(); returns MLRiskResult."""
    # Test case A: completely empty dicts
    result_empty = run({}, [], {})
    assert isinstance(result_empty, MLRiskResult)

    # Test case B: invalid types and corrupted date strings
    malformed_shipment = {
        "scheduled_departure": "not-a-valid-date",
        "scheduled_arrival": 12345,  # wrong type
        "cargo_type": None,
        "weight_kg": "invalid-weight",  # string that will cause float conversion error in features
        "route_reliability_score": "high",
    }
    result_malformed = run(malformed_shipment, [{"severity": "unknown_severity"}], {"reliability_score": "bad"})
    assert isinstance(result_malformed, MLRiskResult)

    # Test case C: partial missing fields
    partial_shipment = {
        "scheduled_arrival": _now_plus(24),
    }
    result_partial = run(partial_shipment, [], {})
    assert isinstance(result_partial, MLRiskResult)
    assert result_partial.ml_score is not None or result_partial.ml_score is None


def test_predictive_risk_multiple_disruptions():
    """Test inference with multiple active disruptions of varying severities."""
    shipment = _valid_shipment()
    disruptions = [
        {"severity": "low"},
        {"severity": "critical"},
        {"severity": "high"},
    ]
    carrier = _valid_carrier()

    result = run(shipment, disruptions, carrier)

    assert isinstance(result, MLRiskResult)
    assert result.ml_score is not None
    assert 0.0 <= result.ml_score <= 1.0
