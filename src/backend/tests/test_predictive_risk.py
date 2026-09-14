"""
Tests for PredictiveRiskEngine — Phase 2B

Run with:
    pytest src/backend/tests/test_predictive_risk.py -v

NOTE: These tests require the risk_model.joblib artifact to be present.
      Run `python -m backend.ml.train` first if you see model-unavailable results.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

from backend.engines.predictive_risk import (
    PredictiveRiskResult,
    _estimate_delay_hours,
    predict_shipment_risk,
    reload_model,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _base_features(**overrides) -> dict:
    base = {
        "disruption_severity_score": 2.0,
        "cargo_value_usd": 50_000,
        "priority_encoded": 1.0,
        "distance_km": 800.0,
        "carrier_reliability": 0.85,
        "temperature_required": 0,
        "is_hazmat": 0,
        "weather_severity": 1.0,
        "route_risk_index": 0.3,
        "hours_until_deadline": 48.0,
        "shipment_age_hours": 10.0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Delay estimation helper
# ---------------------------------------------------------------------------

class TestEstimateDelayHours:
    def test_high_probability_high_delay(self):
        hours = _estimate_delay_hours(0.90, 4.0)
        assert hours >= 36.0

    def test_low_probability_low_delay(self):
        hours = _estimate_delay_hours(0.05, 0.0)
        assert hours == 0.0

    def test_medium_probability_medium_delay(self):
        hours = _estimate_delay_hours(0.60, 2.0)
        assert 10.0 <= hours <= 30.0

    def test_severity_multiplier_increases_delay(self):
        hours_no_disruption = _estimate_delay_hours(0.70, 0.0)
        hours_critical = _estimate_delay_hours(0.70, 4.0)
        assert hours_critical >= hours_no_disruption

    def test_zero_probability_returns_zero(self):
        assert _estimate_delay_hours(0.0, 0.0) == 0.0

    def test_returns_float(self):
        result = _estimate_delay_hours(0.5, 2.0)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# Graceful degradation when model not available
# ---------------------------------------------------------------------------

class TestModelUnavailable:
    def test_returns_unavailable_result_when_no_artifact(self):
        reload_model()
        with patch(
            "backend.engines.predictive_risk._ARTIFACT_PATH",
            new=__import__("pathlib").Path("/nonexistent/path/risk_model.joblib"),
        ):
            reload_model()
            result = predict_shipment_risk(_base_features())
            # Reset after test
            reload_model()

        assert isinstance(result, PredictiveRiskResult)
        assert result.available is False
        assert result.delay_probability == 0.0
        assert result.model_version == "unavailable"

    def test_unavailable_result_has_correct_structure(self):
        with patch("backend.engines.predictive_risk._load_model", return_value=None):
            result = predict_shipment_risk(_base_features())
        assert result.delay_probability == 0.0
        assert result.delay_risk_score == 0.0
        assert result.predicted_delay_hours == 0.0
        assert result.available is False


# ---------------------------------------------------------------------------
# Model inference (when artifact is present)
# ---------------------------------------------------------------------------

class TestModelInference:
    def test_returns_predictive_risk_result(self):
        result = predict_shipment_risk(_base_features())
        assert isinstance(result, PredictiveRiskResult)

    def test_delay_probability_between_0_and_1(self):
        result = predict_shipment_risk(_base_features())
        if result.available:
            assert 0.0 <= result.delay_probability <= 1.0

    def test_risk_score_between_0_and_100(self):
        result = predict_shipment_risk(_base_features())
        if result.available:
            assert 0.0 <= result.delay_risk_score <= 100.0

    def test_predicted_hours_non_negative(self):
        result = predict_shipment_risk(_base_features())
        if result.available:
            assert result.predicted_delay_hours >= 0.0

    def test_model_version_is_string(self):
        result = predict_shipment_risk(_base_features())
        assert isinstance(result.model_version, str)

    def test_risk_score_equals_probability_times_100(self):
        result = predict_shipment_risk(_base_features())
        if result.available:
            assert abs(result.delay_risk_score - result.delay_probability * 100) < 0.1

    def test_high_risk_features_give_higher_probability(self):
        """High-disruption, low-reliability scenario should have higher delay prob."""
        low_risk = _base_features(
            disruption_severity_score=0,
            carrier_reliability=0.98,
            weather_severity=0,
            route_risk_index=0.1,
        )
        high_risk = _base_features(
            disruption_severity_score=4,
            carrier_reliability=0.55,
            weather_severity=4,
            route_risk_index=0.9,
        )
        r_low = predict_shipment_risk(low_risk)
        r_high = predict_shipment_risk(high_risk)
        if r_low.available and r_high.available:
            assert r_high.delay_probability > r_low.delay_probability

    def test_deterministic_for_same_input(self):
        """Same features must always produce the same probability."""
        f = _base_features()
        r1 = predict_shipment_risk(f)
        r2 = predict_shipment_risk(f)
        assert r1.delay_probability == r2.delay_probability

    def test_missing_feature_defaults_gracefully(self):
        """Engine should not crash if optional feature keys are missing."""
        minimal = {"cargo_value_usd": 30_000}
        result = predict_shipment_risk(minimal)
        assert isinstance(result, PredictiveRiskResult)


# ---------------------------------------------------------------------------
# Cargo value log transform
# ---------------------------------------------------------------------------

class TestCargoValueTransform:
    def test_zero_cargo_value_does_not_crash(self):
        f = _base_features(cargo_value_usd=0)
        result = predict_shipment_risk(f)
        assert isinstance(result, PredictiveRiskResult)

    def test_large_cargo_value_handled(self):
        f = _base_features(cargo_value_usd=10_000_000)
        result = predict_shipment_risk(f)
        assert isinstance(result, PredictiveRiskResult)
