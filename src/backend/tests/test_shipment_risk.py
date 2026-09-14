"""
Tests for ShipmentRiskEngine — Phase 2A-2

Run with:
    pytest src/backend/tests/test_shipment_risk.py -v
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.engines.shipment_risk import (
    ShipmentRiskResult,
    _risk_level_from_score,
    calculate_shipment_risk,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _base_shipment(**overrides) -> dict:
    """Minimal valid shipment dict with safe defaults."""
    future = (datetime.now(tz=timezone.utc) + timedelta(hours=72)).isoformat()
    base = {
        "id": "ship-001",
        "tracking_number": "TRK001",
        "status": "in_transit",
        "cargo_type": "general",
        "cargo_value_usd": 10_000,
        "priority": "low",
        "temperature_required": False,
        "scheduled_arrival": future,
        "estimated_arrival": future,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Risk level bands
# ---------------------------------------------------------------------------

class TestRiskLevelBands:
    def test_score_0_is_low(self):
        assert _risk_level_from_score(0) == "LOW"

    def test_score_24_is_low(self):
        assert _risk_level_from_score(24) == "LOW"

    def test_score_25_is_medium(self):
        assert _risk_level_from_score(25) == "MEDIUM"

    def test_score_49_is_medium(self):
        assert _risk_level_from_score(49) == "MEDIUM"

    def test_score_50_is_high(self):
        assert _risk_level_from_score(50) == "HIGH"

    def test_score_74_is_high(self):
        assert _risk_level_from_score(74) == "HIGH"

    def test_score_75_is_critical(self):
        assert _risk_level_from_score(75) == "CRITICAL"

    def test_score_100_is_critical(self):
        assert _risk_level_from_score(100) == "CRITICAL"


# ---------------------------------------------------------------------------
# Cargo value scoring
# ---------------------------------------------------------------------------

class TestCargoValueScoring:
    def test_low_value_adds_5(self):
        ship = _base_shipment(cargo_value_usd=5_000)
        result = calculate_shipment_risk(ship)
        assert any("+5" in f for f in result.factors)

    def test_medium_value_adds_10(self):
        ship = _base_shipment(cargo_value_usd=75_000)
        result = calculate_shipment_risk(ship)
        assert any("+10" in f for f in result.factors)

    def test_high_value_adds_15(self):
        ship = _base_shipment(cargo_value_usd=150_000)
        result = calculate_shipment_risk(ship)
        assert any("+15" in f for f in result.factors)


# ---------------------------------------------------------------------------
# Priority scoring
# ---------------------------------------------------------------------------

class TestPriorityScoring:
    @pytest.mark.parametrize("priority,expected_pts", [
        ("low", 5),
        ("medium", 10),
        ("high", 15),
        ("critical", 20),
    ])
    def test_priority_contribution(self, priority, expected_pts):
        ship = _base_shipment(priority=priority)
        result = calculate_shipment_risk(ship)
        assert any(str(expected_pts) in f for f in result.factors)


# ---------------------------------------------------------------------------
# Deadline proximity
# ---------------------------------------------------------------------------

class TestDeadlineProximity:
    def test_urgent_deadline_adds_20(self):
        urgent = (datetime.now(tz=timezone.utc) + timedelta(hours=6)).isoformat()
        ship = _base_shipment(scheduled_arrival=urgent)
        result = calculate_shipment_risk(ship)
        assert any("+20" in f for f in result.factors)

    def test_soon_deadline_adds_10(self):
        soon = (datetime.now(tz=timezone.utc) + timedelta(hours=18)).isoformat()
        ship = _base_shipment(scheduled_arrival=soon)
        result = calculate_shipment_risk(ship)
        assert any("+10" in f for f in result.factors)

    def test_far_deadline_no_bonus(self):
        far = (datetime.now(tz=timezone.utc) + timedelta(hours=72)).isoformat()
        ship = _base_shipment(scheduled_arrival=far)
        result = calculate_shipment_risk(ship)
        assert not any("Deadline" in f for f in result.factors)


# ---------------------------------------------------------------------------
# Cargo type bonuses
# ---------------------------------------------------------------------------

class TestCargoTypeBonuses:
    def test_temperature_sensitive_adds_10(self):
        ship = _base_shipment(temperature_required=True)
        result = calculate_shipment_risk(ship)
        assert any("+10" in f and "Temperature" in f for f in result.factors)

    def test_temperature_in_cargo_type_adds_10(self):
        ship = _base_shipment(cargo_type="temperature_sensitive")
        result = calculate_shipment_risk(ship)
        assert any("Temperature" in f for f in result.factors)

    def test_hazmat_adds_10(self):
        ship = _base_shipment(cargo_type="hazmat")
        result = calculate_shipment_risk(ship)
        assert any("Hazardous" in f or "hazmat" in f.lower() for f in result.factors)

    def test_general_cargo_no_bonus(self):
        ship = _base_shipment(cargo_type="general", temperature_required=False)
        result = calculate_shipment_risk(ship)
        assert not any("Temperature" in f for f in result.factors)
        assert not any("Hazardous" in f for f in result.factors)


# ---------------------------------------------------------------------------
# At-risk status
# ---------------------------------------------------------------------------

class TestAtRiskStatus:
    @pytest.mark.parametrize("status", ["at_risk", "delayed", "held"])
    def test_at_risk_status_adds_10(self, status):
        ship = _base_shipment(status=status)
        result = calculate_shipment_risk(ship)
        assert any("+10" in f for f in result.factors)

    def test_in_transit_no_bonus(self):
        ship = _base_shipment(status="in_transit")
        result = calculate_shipment_risk(ship)
        assert not any("already" in f for f in result.factors)


# ---------------------------------------------------------------------------
# Disruption impact integration
# ---------------------------------------------------------------------------

class TestDisruptionImpact:
    def test_no_disruption_no_factor(self):
        ship = _base_shipment()
        result = calculate_shipment_risk(ship, disruption_impact_score=None)
        assert not any("disruption" in f.lower() for f in result.factors)

    def test_disruption_contributes_proportionally(self):
        ship = _base_shipment()
        result = calculate_shipment_risk(ship, disruption_impact_score=100.0)
        # 100 * 0.40 = 40 pts contribution
        assert any("40.0" in f or "40" in f for f in result.factors)

    def test_high_disruption_raises_level(self):
        ship = _base_shipment(
            cargo_value_usd=200_000,
            priority="critical",
            status="at_risk",
        )
        result = calculate_shipment_risk(ship, disruption_impact_score=80.0)
        assert result.risk_level in ("HIGH", "CRITICAL")


# ---------------------------------------------------------------------------
# ML score blending
# ---------------------------------------------------------------------------

class TestMLBlending:
    def test_no_ml_uses_deterministic_only(self):
        ship = _base_shipment(cargo_value_usd=200_000, priority="critical")
        result_no_ml = calculate_shipment_risk(ship, ml_risk_score=None)
        result_with_ml = calculate_shipment_risk(ship, ml_risk_score=50.0)
        # ml_score should be None for no-ML case
        assert result_no_ml.ml_score is None
        assert result_with_ml.ml_score == 50.0

    def test_ml_score_blended_correctly(self):
        ship = _base_shipment(cargo_value_usd=5_000, priority="low")
        # Deterministic score should be low; ML score will raise it
        result = calculate_shipment_risk(ship, ml_risk_score=90.0)
        assert result.ml_score == 90.0
        # blended should be > deterministic alone
        assert result.risk_score > result.deterministic_score * 0.60

    def test_ml_score_factor_mentioned_in_output(self):
        ship = _base_shipment()
        result = calculate_shipment_risk(ship, ml_risk_score=75.0)
        assert any("ML" in f for f in result.factors)


# ---------------------------------------------------------------------------
# Score capping
# ---------------------------------------------------------------------------

class TestScoreCapping:
    def test_score_never_exceeds_100(self):
        far_future = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
        ship = _base_shipment(
            cargo_value_usd=500_000,
            priority="critical",
            cargo_type="hazmat",
            temperature_required=True,
            status="at_risk",
            scheduled_arrival=far_future,
        )
        result = calculate_shipment_risk(
            ship,
            disruption_impact_score=100.0,
            ml_risk_score=100.0,
        )
        assert result.risk_score <= 100.0
        assert result.deterministic_score <= 100.0

    def test_score_never_below_0(self):
        ship = _base_shipment()
        result = calculate_shipment_risk(ship, ml_risk_score=0.0)
        assert result.risk_score >= 0.0


# ---------------------------------------------------------------------------
# Return type and determinism
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_returns_dataclass(self):
        ship = _base_shipment()
        result = calculate_shipment_risk(ship)
        assert isinstance(result, ShipmentRiskResult)

    def test_factors_is_list_of_strings(self):
        ship = _base_shipment()
        result = calculate_shipment_risk(ship)
        assert isinstance(result.factors, list)
        assert all(isinstance(f, str) for f in result.factors)

    def test_deterministic_execution(self):
        """Same inputs must always produce same outputs."""
        ship = _base_shipment(cargo_value_usd=80_000, priority="high")
        r1 = calculate_shipment_risk(ship, disruption_impact_score=50.0, ml_risk_score=60.0)
        r2 = calculate_shipment_risk(ship, disruption_impact_score=50.0, ml_risk_score=60.0)
        assert r1.risk_score == r2.risk_score
        assert r1.risk_level == r2.risk_level
        assert r1.factors == r2.factors
