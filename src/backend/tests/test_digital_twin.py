"""
Tests for DigitalTwinEngine — Phase 2E

Run with:
    pytest src/backend/tests/test_digital_twin.py -v
"""

from __future__ import annotations

import pytest

from backend.engines.digital_twin import (
    DigitalTwinResult,
    ScenarioDelta,
    ScenarioSnapshot,
    _compute_confidence,
    _risk_level_from_score,
    run_digital_twin,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current(
    shipment_id: str = "S001",
    tracking_number: str = "TRK001",
    route_id: str = "R001",
    carrier_id: str = "C001",
    estimated_hours: float = 24.0,
    total_cost_usd: float = 1000.0,
    risk_score: float = 60.0,
    risk_level: str = "HIGH",
    on_time_probability: float = 0.55,
) -> dict:
    return {
        "shipment_id": shipment_id,
        "tracking_number": tracking_number,
        "current_route_id": route_id,
        "current_carrier_id": carrier_id,
        "estimated_hours": estimated_hours,
        "total_cost_usd": total_cost_usd,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "on_time_probability": on_time_probability,
    }


def _sim_changes(**kwargs) -> dict:
    return kwargs


# ---------------------------------------------------------------------------
# Risk level helper
# ---------------------------------------------------------------------------

class TestRiskLevelFromScore:
    def test_low(self):      assert _risk_level_from_score(10) == "LOW"
    def test_medium(self):   assert _risk_level_from_score(30) == "MEDIUM"
    def test_high(self):     assert _risk_level_from_score(60) == "HIGH"
    def test_critical(self): assert _risk_level_from_score(80) == "CRITICAL"


# ---------------------------------------------------------------------------
# Snapshot building
# ---------------------------------------------------------------------------

class TestSnapshotBuilding:
    def test_current_snapshot_populated(self):
        result = run_digital_twin(_current(), _sim_changes())
        c = result.current
        assert c.shipment_id == "S001"
        assert c.estimated_hours == 24.0
        assert c.risk_score == 60.0

    def test_simulated_uses_current_as_fallback(self):
        """When no changes provided, simulated == current."""
        result = run_digital_twin(_current(), {})
        assert result.current.risk_score == result.simulated.risk_score
        assert result.current.estimated_hours == result.simulated.estimated_hours

    def test_simulated_overrides_provided_fields(self):
        result = run_digital_twin(
            _current(estimated_hours=24.0),
            _sim_changes(simulated_estimated_hours=18.0),
        )
        assert result.simulated.estimated_hours == 18.0
        assert result.current.estimated_hours == 24.0

    def test_simulated_risk_level_derived_from_score(self):
        result = run_digital_twin(
            _current(),
            _sim_changes(simulated_risk_score=20.0),
        )
        assert result.simulated.risk_level == "LOW"


# ---------------------------------------------------------------------------
# Delta calculation
# ---------------------------------------------------------------------------

class TestDeltaCalculation:
    def test_faster_eta_gives_negative_hours_delta(self):
        result = run_digital_twin(
            _current(estimated_hours=24.0),
            _sim_changes(simulated_estimated_hours=18.0),
        )
        assert result.delta.hours_delta == pytest.approx(-6.0)

    def test_cheaper_cost_gives_negative_cost_delta(self):
        result = run_digital_twin(
            _current(total_cost_usd=1000.0),
            _sim_changes(simulated_total_cost_usd=800.0),
        )
        assert result.delta.cost_delta_usd == pytest.approx(-200.0)

    def test_lower_risk_gives_negative_risk_delta(self):
        result = run_digital_twin(
            _current(risk_score=65.0),
            _sim_changes(simulated_risk_score=30.0),
        )
        assert result.delta.risk_score_delta == pytest.approx(-35.0)

    def test_no_change_all_deltas_zero(self):
        cur = _current()
        result = run_digital_twin(cur, {})
        assert result.delta.hours_delta == 0.0
        assert result.delta.cost_delta_usd == 0.0
        assert result.delta.risk_score_delta == 0.0

    def test_on_time_delta_calculated(self):
        result = run_digital_twin(
            _current(on_time_probability=0.55),
            _sim_changes(simulated_on_time_probability=0.85),
        )
        assert result.delta.on_time_delta == pytest.approx(0.30, abs=0.001)


# ---------------------------------------------------------------------------
# SWITCH / KEEP recommendation
# ---------------------------------------------------------------------------

class TestRecommendation:
    def test_significant_improvement_recommends_switch(self):
        result = run_digital_twin(
            _current(risk_score=70.0, on_time_probability=0.50, total_cost_usd=1000.0),
            _sim_changes(
                simulated_risk_score=25.0,          # big risk drop
                simulated_on_time_probability=0.85, # on-time improves
                simulated_total_cost_usd=1100.0,    # ≤20% cost increase
                simulated_estimated_hours=25.0,     # ≤4h slower
            ),
        )
        assert result.recommendation == "SWITCH"

    def test_no_improvement_recommends_keep(self):
        """Same scenario as current — no reason to switch."""
        cur = _current()
        result = run_digital_twin(cur, {})
        assert result.recommendation == "KEEP"

    def test_excessive_cost_increase_recommends_keep(self):
        result = run_digital_twin(
            _current(risk_score=70.0, total_cost_usd=1000.0),
            _sim_changes(
                simulated_risk_score=30.0,         # risk improves
                simulated_total_cost_usd=2500.0,   # 150% cost increase — rejected
            ),
        )
        assert result.recommendation == "KEEP"

    def test_excessive_delay_recommends_keep(self):
        result = run_digital_twin(
            _current(risk_score=70.0, estimated_hours=10.0),
            _sim_changes(
                simulated_risk_score=30.0,          # risk improves
                simulated_estimated_hours=20.0,     # 10h slower — rejected
            ),
        )
        assert result.recommendation == "KEEP"


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    def test_confidence_between_0_and_1(self):
        result = run_digital_twin(_current(), {})
        assert 0.0 <= result.confidence <= 1.0

    def test_high_improvement_gives_higher_confidence(self):
        r_big = run_digital_twin(
            _current(risk_score=80.0, on_time_probability=0.40),
            _sim_changes(simulated_risk_score=10.0, simulated_on_time_probability=0.95),
        )
        r_small = run_digital_twin(
            _current(risk_score=55.0, on_time_probability=0.70),
            _sim_changes(simulated_risk_score=50.0, simulated_on_time_probability=0.72),
        )
        assert r_big.confidence > r_small.confidence

    def test_critical_simulated_risk_reduces_confidence(self):
        result = run_digital_twin(
            _current(risk_score=80.0),
            _sim_changes(simulated_risk_score=76.0),  # still CRITICAL
        )
        # Even if slightly better, confidence should be penalised
        assert result.confidence < 0.5


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_returns_digital_twin_result(self):
        result = run_digital_twin(_current(), {})
        assert isinstance(result, DigitalTwinResult)

    def test_contains_current_and_simulated(self):
        result = run_digital_twin(_current(), {})
        assert isinstance(result.current, ScenarioSnapshot)
        assert isinstance(result.simulated, ScenarioSnapshot)

    def test_contains_delta(self):
        result = run_digital_twin(_current(), {})
        assert isinstance(result.delta, ScenarioDelta)

    def test_factors_list_of_strings(self):
        result = run_digital_twin(_current(), {})
        assert all(isinstance(f, str) for f in result.factors)

    def test_recommendation_is_valid_string(self):
        result = run_digital_twin(_current(), {})
        assert result.recommendation in ("SWITCH", "KEEP")

    def test_deterministic_same_input(self):
        cur = _current()
        sim = _sim_changes(simulated_risk_score=20.0)
        r1 = run_digital_twin(cur, sim)
        r2 = run_digital_twin(cur, sim)
        assert r1.recommendation == r2.recommendation
        assert r1.confidence == r2.confidence
