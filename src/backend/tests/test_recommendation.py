"""
Tests for RecommendationEngine — Phase 2F

Run with:
    pytest src/backend/tests/test_recommendation.py -v

Strategy:
  - Uses lightweight mock objects (SimpleNamespace / plain dicts)
    so no real engine instances are needed.
  - Tests all action paths, urgency levels, field population,
    graceful degradation with None inputs, and determinism.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

import pytest

from backend.engines.recommendation import (
    ACTION_CARRIER_SWAP,
    ACTION_COLD_CHAIN_ALERT,
    ACTION_EXPEDITE,
    ACTION_HOLD_AND_MONITOR,
    ACTION_NO_ACTION,
    ACTION_REROUTE,
    ACTION_VEHICLE_REASSIGN,
    RecommendationBundle,
    _get_attr,
    _urgency_from_score,
    synthesize_recommendation,
)


# ---------------------------------------------------------------------------
# Mock helpers — lightweight stand-ins for engine dataclasses
# ---------------------------------------------------------------------------

def _risk(score: float = 0.0, level: str = "LOW"):
    return SimpleNamespace(risk_score=score, risk_level=level)


def _predictive(available: bool = True, prob: float = 0.0, hours: float = 0.0):
    return SimpleNamespace(available=available, delay_probability=prob,
                           predicted_delay_hours=hours)


def _cold_chain(severity: str = "NONE", spoilage: float = 0.0):
    return SimpleNamespace(has_excursion=severity != "NONE",
                           excursion_severity=severity,
                           spoilage_risk_percent=spoilage)


def _fleet(candidates: list = None):
    return SimpleNamespace(redeployment_candidates=candidates or [])


def _vehicle_candidate(id: str = "V001", code: str = "TRK-001", score: float = 80.0):
    return SimpleNamespace(id=id, vehicle_code=code, suitability_score=score)


def _route_result(route_id: str = "R001", name: str = "Route A", score: float = 75.0):
    rec = SimpleNamespace(id=route_id, name=name, composite_score=score)
    return SimpleNamespace(recommended_route=rec, ranked_routes=[rec])


def _carrier_result(carrier_id: str = "C001", name: str = "FastShip", on_time: float = 0.92):
    rec = SimpleNamespace(id=carrier_id, name=name, on_time_rate=on_time)
    return SimpleNamespace(recommended_carrier=rec, ranked_carriers=[rec])


def _cascade(total: int = 0):
    return SimpleNamespace(total_affected_count=total,
                           potentially_delayed_shipments=[],
                           vehicle_conflicts=[])


def _twin(recommendation: str = "KEEP", confidence: float = 0.70):
    return SimpleNamespace(recommendation=recommendation, confidence=confidence)


def _business(
    cargo_risk: float = 5000.0,
    sla: float = 2000.0,
    transport: float = 1000.0,
    total: float = 8000.0,
    risk_pct: float = 8.0,
):
    return SimpleNamespace(
        cargo_value_at_risk_usd=cargo_risk,
        sla_penalty_usd=sla,
        extra_transport_cost_usd=transport,
        total_financial_exposure_usd=total,
        risk_percentage=risk_pct,
    )


def _ship_ctx(
    id: str = "S001",
    tracking_number: str = "TRK001",
    priority: str = "medium",
    temperature_required: bool = False,
) -> dict:
    return {
        "id": id,
        "tracking_number": tracking_number,
        "priority": priority,
        "temperature_required": temperature_required,
    }


# ---------------------------------------------------------------------------
# _get_attr helper
# ---------------------------------------------------------------------------

class TestGetAttr:
    def test_reads_namespace_attribute(self):
        obj = SimpleNamespace(foo=42)
        assert _get_attr(obj, "foo") == 42

    def test_reads_dict_key(self):
        obj = {"bar": "hello"}
        assert _get_attr(obj, "bar") == "hello"

    def test_returns_default_when_missing(self):
        assert _get_attr(None, "anything", default="X") == "X"

    def test_returns_default_when_attr_is_none(self):
        obj = SimpleNamespace(val=None)
        assert _get_attr(obj, "val", default=99) == 99


# ---------------------------------------------------------------------------
# _urgency_from_score
# ---------------------------------------------------------------------------

class TestUrgencyFromScore:
    def test_critical(self):   assert _urgency_from_score(80.0) == "CRITICAL"
    def test_high(self):       assert _urgency_from_score(55.0) == "HIGH"
    def test_medium(self):     assert _urgency_from_score(30.0) == "MEDIUM"
    def test_low(self):        assert _urgency_from_score(10.0) == "LOW"
    def test_zero_is_low(self): assert _urgency_from_score(0.0) == "LOW"


# ---------------------------------------------------------------------------
# All-None inputs — graceful degradation
# ---------------------------------------------------------------------------

class TestGracefulDegradation:
    def test_all_none_inputs_returns_bundle(self):
        result = synthesize_recommendation(_ship_ctx())
        assert isinstance(result, RecommendationBundle)

    def test_all_none_action_is_no_action(self):
        result = synthesize_recommendation(_ship_ctx())
        assert result.recommended_action == ACTION_NO_ACTION

    def test_all_none_targets_are_none(self):
        result = synthesize_recommendation(_ship_ctx())
        assert result.target_route_id is None
        assert result.target_carrier_id is None
        assert result.target_vehicle_id is None

    def test_all_none_confidence_is_reasonable(self):
        result = synthesize_recommendation(_ship_ctx())
        assert 0.0 <= result.confidence_score <= 1.0

    def test_all_none_reasons_not_empty(self):
        result = synthesize_recommendation(_ship_ctx())
        assert len(result.reasons) >= 1

    def test_all_none_business_impact_empty_dict(self):
        result = synthesize_recommendation(_ship_ctx())
        assert isinstance(result.business_impact, dict)


# ---------------------------------------------------------------------------
# Action selection logic
# ---------------------------------------------------------------------------

class TestActionSelection:
    def test_cold_chain_critical_overrides_all(self):
        """COLD_CHAIN_ALERT must be selected even when risk is LOW."""
        result = synthesize_recommendation(
            _ship_ctx(),
            risk_result=_risk(score=5.0, level="LOW"),
            cold_chain_result=_cold_chain(severity="CRITICAL", spoilage=90.0),
        )
        assert result.recommended_action == ACTION_COLD_CHAIN_ALERT
        assert result.cold_chain_alert is True

    def test_cold_chain_major_triggers_alert(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            cold_chain_result=_cold_chain(severity="MAJOR", spoilage=45.0),
        )
        assert result.recommended_action == ACTION_COLD_CHAIN_ALERT

    def test_reroute_when_critical_risk_and_twin_switch(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            risk_result=_risk(score=80.0, level="CRITICAL"),
            route_result=_route_result(),
            twin_result=_twin(recommendation="SWITCH", confidence=0.85),
        )
        assert result.recommended_action == ACTION_REROUTE
        assert result.target_route_id == "R001"

    def test_carrier_swap_when_critical_no_route(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            risk_result=_risk(score=80.0, level="CRITICAL"),
            carrier_result=_carrier_result(),
        )
        assert result.recommended_action == ACTION_CARRIER_SWAP
        assert result.target_carrier_id == "C001"

    def test_vehicle_reassign_when_high_risk_and_candidate(self):
        candidate = _vehicle_candidate()
        result = synthesize_recommendation(
            _ship_ctx(),
            risk_result=_risk(score=65.0, level="HIGH"),
            fleet_result=_fleet([candidate]),
        )
        assert result.recommended_action == ACTION_VEHICLE_REASSIGN
        assert result.target_vehicle_id == "V001"

    def test_expedite_when_high_risk_high_delay_prob(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            risk_result=_risk(score=55.0, level="HIGH"),
            predictive_result=_predictive(available=True, prob=0.75, hours=18.0),
        )
        assert result.recommended_action == ACTION_EXPEDITE

    def test_hold_and_monitor_for_medium_risk(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            risk_result=_risk(score=40.0, level="MEDIUM"),
        )
        assert result.recommended_action == ACTION_HOLD_AND_MONITOR

    def test_no_action_for_low_risk(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            risk_result=_risk(score=10.0, level="LOW"),
        )
        assert result.recommended_action == ACTION_NO_ACTION


# ---------------------------------------------------------------------------
# Field population
# ---------------------------------------------------------------------------

class TestFieldPopulation:
    def test_shipment_id_and_tracking_number(self):
        result = synthesize_recommendation(_ship_ctx(id="SHP-X", tracking_number="TRK-X"))
        assert result.shipment_id == "SHP-X"
        assert result.tracking_number == "TRK-X"

    def test_target_route_id_populated(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            route_result=_route_result(route_id="RT-99"),
        )
        assert result.target_route_id == "RT-99"

    def test_target_carrier_id_populated(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            carrier_result=_carrier_result(carrier_id="CAR-55"),
        )
        assert result.target_carrier_id == "CAR-55"

    def test_target_vehicle_id_populated(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            fleet_result=_fleet([_vehicle_candidate(id="VEH-77")]),
        )
        assert result.target_vehicle_id == "VEH-77"

    def test_cascade_affected_count_populated(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            cascade_result=_cascade(total=5),
        )
        assert result.cascade_affected_count == 5

    def test_business_impact_dict_populated(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            business_result=_business(total=50_000.0, risk_pct=25.0),
        )
        assert result.business_impact["total_financial_exposure_usd"] == pytest.approx(50_000.0)
        assert result.business_impact["risk_percentage"] == pytest.approx(25.0)

    def test_digital_twin_advice_populated(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            twin_result=_twin(recommendation="SWITCH"),
        )
        assert result.digital_twin_advice == "SWITCH"

    def test_digital_twin_advice_none_when_no_twin(self):
        result = synthesize_recommendation(_ship_ctx())
        assert result.digital_twin_advice is None


# ---------------------------------------------------------------------------
# Urgency level
# ---------------------------------------------------------------------------

class TestUrgencyLevel:
    def test_critical_risk_score_gives_critical_urgency(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            risk_result=_risk(score=80.0, level="CRITICAL"),
        )
        assert result.urgency_level == "CRITICAL"

    def test_low_risk_score_gives_low_urgency(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            risk_result=_risk(score=5.0, level="LOW"),
        )
        assert result.urgency_level == "LOW"


# ---------------------------------------------------------------------------
# Reasons list
# ---------------------------------------------------------------------------

class TestReasonsList:
    def test_reasons_is_list_of_strings(self):
        result = synthesize_recommendation(_ship_ctx(), risk_result=_risk(80.0, "CRITICAL"))
        assert all(isinstance(r, str) for r in result.reasons)

    def test_risk_reason_present_when_high(self):
        result = synthesize_recommendation(_ship_ctx(), risk_result=_risk(70.0, "HIGH"))
        assert any("risk score" in r.lower() for r in result.reasons)

    def test_cold_chain_reason_present_when_alert(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            cold_chain_result=_cold_chain("CRITICAL", 90.0),
        )
        assert any("cold chain" in r.lower() for r in result.reasons)

    def test_cascade_reason_present_when_affected(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            cascade_result=_cascade(total=3),
        )
        assert any("cascade" in r.lower() for r in result.reasons)


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    def test_confidence_between_0_and_1(self):
        result = synthesize_recommendation(_ship_ctx())
        assert 0.0 <= result.confidence_score <= 1.0

    def test_multiple_signals_contribute_to_confidence(self):
        result = synthesize_recommendation(
            _ship_ctx(),
            predictive_result=_predictive(available=True, prob=0.90, hours=20.0),
            twin_result=_twin(recommendation="SWITCH", confidence=0.85),
            cascade_result=_cascade(total=4),
        )
        assert result.confidence_score > 0.5


# ---------------------------------------------------------------------------
# Full integration with all inputs
# ---------------------------------------------------------------------------

class TestFullIntegration:
    def test_full_bundle_with_all_inputs(self):
        """Smoke test: all inputs provided → valid bundle produced."""
        result = synthesize_recommendation(
            shipment_context=_ship_ctx(id="S-FULL", tracking_number="TRK-FULL"),
            risk_result=_risk(score=78.0, level="CRITICAL"),
            predictive_result=_predictive(available=True, prob=0.82, hours=22.0),
            cold_chain_result=_cold_chain(severity="NONE"),
            fleet_result=_fleet([_vehicle_candidate()]),
            route_result=_route_result(),
            carrier_result=_carrier_result(),
            cascade_result=_cascade(total=3),
            twin_result=_twin(recommendation="SWITCH", confidence=0.80),
            business_result=_business(total=95_000.0, risk_pct=19.0),
        )
        assert isinstance(result, RecommendationBundle)
        assert result.shipment_id == "S-FULL"
        assert result.recommended_action in (
            ACTION_REROUTE, ACTION_CARRIER_SWAP, ACTION_VEHICLE_REASSIGN,
            ACTION_COLD_CHAIN_ALERT, ACTION_EXPEDITE, ACTION_HOLD_AND_MONITOR,
            ACTION_NO_ACTION,
        )
        assert result.urgency_level == "CRITICAL"
        assert len(result.reasons) >= 3
        assert result.cascade_affected_count == 3
        assert not result.cold_chain_alert

    def test_deterministic_full_run(self):
        kwargs = dict(
            shipment_context=_ship_ctx(),
            risk_result=_risk(60.0, "HIGH"),
            predictive_result=_predictive(True, 0.65, 14.0),
            cold_chain_result=_cold_chain("MAJOR", 45.0),
            cascade_result=_cascade(3),
            twin_result=_twin("SWITCH", 0.75),
            business_result=_business(),
        )
        r1 = synthesize_recommendation(**kwargs)
        r2 = synthesize_recommendation(**kwargs)
        assert r1.recommended_action == r2.recommended_action
        assert r1.confidence_score == r2.confidence_score
        assert r1.urgency_level == r2.urgency_level
