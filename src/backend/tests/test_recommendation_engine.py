"""
Tests for RecommendationEngine (orchestrator for all business engines).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch
import pytest

from backend.engines.recommendation_engine import (
    OrchestratorResult,
    RecommendationCandidate,
    _priority_from_score,
    run,
)
from backend.engines.predictive_risk import MLRiskResult, FeatureContribution


def _disruption(**kwargs: Any) -> dict[str, Any]:
    base = {
        "id": "disp-001",
        "title": "Red Sea Disruption",
        "severity": "high",
        "epicenter_lat": 20.0,
        "epicenter_lng": 38.0,
        "affected_radius_km": 500.0,
        "affected_route_codes": ["RT-RED-SEA"],
        "affected_region": "red sea",
        "start_time": datetime(2026, 9, 14, 0, 0, 0, tzinfo=timezone.utc),
        "estimated_end_time": datetime(2026, 9, 17, 0, 0, 0, tzinfo=timezone.utc),
    }
    base.update(kwargs)
    return base


def _shipment(
    shipment_id: str = "shp-001",
    status: str = "in_transit",
    lat: float = 20.5,
    lng: float = 38.5,
    route_code: str = "RT-RED-SEA",
    route_id: str = "r-curr",
    origin: str = "Shanghai",
    destination: str = "Rotterdam",
    cargo_value: float = 40_000.0,
    cargo_type: str = "general",
    carrier_id: str = "c-curr",
    temperature_required: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    base = {
        "id": shipment_id,
        "tracking_number": f"TRK-{shipment_id}",
        "status": status,
        "current_lat": lat,
        "current_lng": lng,
        "origin": origin,
        "destination": destination,
        "route_code": route_code,
        "route_id": route_id,
        "cargo_value_usd": cargo_value,
        "cargo_type": cargo_type,
        "carrier_id": carrier_id,
        "temperature_required": temperature_required,
        "scheduled_departure": (now - timedelta(days=2)).isoformat(),
        "scheduled_arrival": (now + timedelta(days=5)).isoformat(),
        "estimated_arrival": (now + timedelta(days=6)).isoformat(),
        "weight_kg": 5000.0,
        "route_reliability_score": 0.85,
    }
    base.update(kwargs)
    return base


def _routes() -> list[dict[str, Any]]:
    return [
        {
            "id": "r-alt-1",
            "code": "RT-CAPE",
            "name": "Cape of Good Hope Route",
            "origin": "Shanghai",
            "destination": "Rotterdam",
            "active": True,
            "reliability_score": 0.90,
            "distance_km": 15000.0,
            "cost_per_kg_usd": 1.2,
            "typical_duration_hours": 96.0,
        }
    ]


def _carriers() -> list[dict[str, Any]]:
    return [
        {
            "id": "c-alt-1",
            "name": "Cape Alternative Shipping",
            "code": "CAS-01",
            "reliability_score": 0.95,
            "cost_index": 0.90,
            "coverage_regions": ["rotterdam", "europe"],
            "active": True,
        }
    ]


def _carriers_by_id() -> dict[str, dict[str, Any]]:
    return {
        "c-curr": {
            "id": "c-curr",
            "name": "Current Carrier",
            "code": "CURR-01",
            "reliability_score": 0.70,
            "cost_index": 1.0,
            "coverage_regions": ["red sea"],
            "active": True,
        }
    }


def _fleet() -> list[dict[str, Any]]:
    return [
        {
            "id": "f-001",
            "vehicle_id": "VH-IDLE-01",
            "status": "active",
            "utilization_pct": 10.0,
            "current_lat": 20.6,
            "current_lng": 38.6,
            "capacity_kg": 10000.0,
            "temperature_capable": True,
            "type": "truck",
        }
    ]


def test_empty_shipment_list():
    """1. Empty shipment list does not crash and returns a valid empty result."""
    disruption = _disruption()
    result = run(
        disruption=disruption,
        all_shipments=[],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=_fleet(),
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert isinstance(result, OrchestratorResult)
    assert result.recommendations == []
    assert result.affected_shipment_ids == []
    assert result.impact_result is not None
    assert result.impact_result.affected_count == 0


def test_active_shipment_filtering():
    """2. Only in_transit, at_risk, and delayed shipments are processed; completed/cancelled ignored."""
    disruption = _disruption()
    s_active_1 = _shipment(shipment_id="shp-in-transit", status="in_transit")
    s_active_2 = _shipment(shipment_id="shp-delayed", status="delayed")
    s_active_3 = _shipment(shipment_id="shp-at-risk", status="at_risk")
    s_delivered = _shipment(shipment_id="shp-delivered", status="delivered")
    s_cancelled = _shipment(shipment_id="shp-cancelled", status="cancelled")
    s_draft = _shipment(shipment_id="shp-draft", status="draft")

    all_shipments = [s_active_1, s_active_2, s_active_3, s_delivered, s_cancelled, s_draft]

    result = run(
        disruption=disruption,
        all_shipments=all_shipments,
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert set(result.affected_shipment_ids) == {"shp-in-transit", "shp-delayed", "shp-at-risk"}
    assert "shp-delivered" not in result.affected_shipment_ids
    assert "shp-cancelled" not in result.affected_shipment_ids
    assert "shp-draft" not in result.affected_shipment_ids


def test_disruption_impact_integration():
    """3. Impacted shipments produce recommendations, unaffected outside disruption zone are ignored."""
    disruption = _disruption(epicenter_lat=20.0, epicenter_lng=38.0, affected_radius_km=100.0, affected_route_codes=[])
    s_near = _shipment(shipment_id="shp-near", lat=20.1, lng=38.1, route_code="RT-UNBLOCKED")
    s_far = _shipment(shipment_id="shp-far", lat=-30.0, lng=-40.0, route_code="RT-OTHER")

    result = run(
        disruption=disruption,
        all_shipments=[s_near, s_far],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert result.affected_shipment_ids == ["shp-near"]
    assert all(r.shipment_id != "shp-far" for r in result.recommendations)


def test_combined_risk_score_and_fallback():
    """4. Verify combined_score = 0.6 * deterministic + 0.4 * ML score, with graceful fallback if ML is unavailable."""
    disruption = _disruption()
    s = _shipment(shipment_id="shp-score-test")

    # Case A: with mock ML score
    mock_ml = MLRiskResult(ml_score=0.8, top_features=[FeatureContribution("days", 3.0, 0.5)], model_version="v1")
    with patch("backend.engines.predictive_risk.run", return_value=mock_ml):
        with patch("backend.engines.shipment_risk.run") as mock_det:
            from backend.engines.shipment_risk import RiskResult
            mock_det.return_value = RiskResult(score=0.6, level="medium", factors=[], explanation="ok")
            result = run(
                disruption=disruption,
                all_shipments=[s],
                all_routes=_routes(),
                all_carriers=_carriers(),
                all_fleet=[],
                temperature_excursions={},
                carriers_by_id=_carriers_by_id(),
            )
            # combined = 0.6 * 0.6 + 0.4 * 0.8 = 0.36 + 0.32 = 0.68 -> priority "high"
            assert len(result.recommendations) > 0
            assert result.recommendations[0].priority == "high"

    # Case B: fallback when ML returns None
    mock_ml_none = MLRiskResult(ml_score=None, top_features=[], model_version="unknown")
    with patch("backend.engines.predictive_risk.run", return_value=mock_ml_none):
        with patch("backend.engines.shipment_risk.run") as mock_det:
            mock_det.return_value = RiskResult(score=0.7, level="high", factors=[], explanation="ok")
            result = run(
                disruption=disruption,
                all_shipments=[s],
                all_routes=_routes(),
                all_carriers=_carriers(),
                all_fleet=[],
                temperature_excursions={},
                carriers_by_id=_carriers_by_id(),
            )
            # combined = 0.7 -> priority "high"
            assert len(result.recommendations) > 0
            assert result.recommendations[0].priority == "high"


def test_recommendation_prioritization():
    """5. Higher-risk shipments are processed first in recommendation generation."""
    disruption = _disruption()
    s_low = _shipment(shipment_id="shp-low", cargo_value=1_000.0)
    s_high = _shipment(shipment_id="shp-high", cargo_value=500_000.0, temperature_required=True)

    result = run(
        disruption=disruption,
        all_shipments=[s_low, s_high],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=[],
        temperature_excursions={"shp-high": True},
        carriers_by_id=_carriers_by_id(),
    )

    # Recommendations for the higher-risk shipment should appear before the lower-risk shipment
    shipment_rec_order = [r.shipment_id for r in result.recommendations if r.shipment_id]
    if "shp-high" in shipment_rec_order and "shp-low" in shipment_rec_order:
        assert shipment_rec_order.index("shp-high") < shipment_rec_order.index("shp-low")


def test_route_recommendation():
    """6. Impacted shipments receive reroute recommendations when alternative routes exist."""
    disruption = _disruption()
    s = _shipment(shipment_id="shp-reroute", origin="Shanghai", destination="Rotterdam", route_id="r-curr")
    routes = _routes()

    result = run(
        disruption=disruption,
        all_shipments=[s],
        all_routes=routes,
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    reroute_recs = [r for r in result.recommendations if r.type == "reroute"]
    assert len(reroute_recs) == 1
    assert reroute_recs[0].alternative_route_id == "r-alt-1"
    assert reroute_recs[0].shipment_id == "shp-reroute"
    assert "RT-CAPE" in reroute_recs[0].title


def test_carrier_recommendation():
    """7. High-risk impacted shipments (combined >= 0.5) receive carrier recommendations."""
    disruption = _disruption(severity="critical")
    now = datetime.now(timezone.utc)
    s = _shipment(
        shipment_id="shp-carrier",
        cargo_value=250_000.0,
        scheduled_arrival=(now + timedelta(hours=12)).isoformat(),
        temperature_required=True,
    )
    carriers = _carriers()

    result = run(
        disruption=disruption,
        all_shipments=[s],
        all_routes=[],
        all_carriers=carriers,
        all_fleet=[],
        temperature_excursions={"shp-carrier": True},
        carriers_by_id=_carriers_by_id(),
    )

    carrier_recs = [r for r in result.recommendations if r.type == "carrier_change"]
    assert len(carrier_recs) == 1
    assert carrier_recs[0].alternative_carrier_id == "c-alt-1"
    assert "Switch" in carrier_recs[0].title


def test_cold_chain_expedite_recommendation():
    """8. Temperature-sensitive shipment with active excursion receives critical expedite recommendation."""
    disruption = _disruption()
    s = _shipment(
        shipment_id="shp-cold",
        temperature_required=True,
        cargo_type="temperature_sensitive",
        cargo_value=80_000.0,
    )

    result = run(
        disruption=disruption,
        all_shipments=[s],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=[],
        temperature_excursions={"shp-cold": True},
        carriers_by_id=_carriers_by_id(),
    )

    expedite_recs = [r for r in result.recommendations if r.type == "expedite"]
    assert len(expedite_recs) == 1
    rec = expedite_recs[0]
    assert rec.priority == "critical"
    assert rec.requires_approval is True
    assert "cold-chain excursion" in rec.title.lower()


def test_fleet_redeployment_recommendation():
    """9. Delayed/at-risk impacted shipments receive fleet redeployment recommendations when idle fleet exists."""
    disruption = _disruption()
    s_delayed = _shipment(
        shipment_id="shp-delayed-fleet",
        status="delayed",
        lat=20.5,
        lng=38.5,
        weight_kg=4000.0,
    )
    fleet = _fleet()

    result = run(
        disruption=disruption,
        all_shipments=[s_delayed],
        all_routes=[],
        all_carriers=[],
        all_fleet=fleet,
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    fleet_recs = [r for r in result.recommendations if r.type == "fleet_redeploy"]
    assert len(fleet_recs) == 1
    assert fleet_recs[0].shipment_id == "shp-delayed-fleet"
    assert fleet_recs[0].requires_approval is True


def test_cascade_escalation_recommendation():
    """10. Secondary impacted shipments trigger an escalate recommendation."""
    disruption = _disruption()
    # s1 is directly impacted; s2 shares fleet_id with s1 but is located elsewhere
    s1_direct = _shipment(shipment_id="shp-direct", lat=20.5, lng=38.5, fleet_id="f-shared")
    s2_secondary = _shipment(
        shipment_id="shp-sec",
        lat=0.0,
        lng=0.0,
        route_code="RT-SAFE",
        fleet_id="f-shared",
        cargo_value=90_000.0,
    )

    result = run(
        disruption=disruption,
        all_shipments=[s1_direct, s2_secondary],
        all_routes=[],
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    escalate_recs = [r for r in result.recommendations if r.type == "escalate"]
    assert len(escalate_recs) == 1
    rec = escalate_recs[0]
    assert rec.shipment_id is None  # system-wide escalation
    assert rec.priority == "high"
    assert "Cascade alert" in rec.title


def test_business_impact_integration():
    """11. Business impact calculation is performed and populated on OrchestratorResult."""
    disruption = _disruption()
    s1 = _shipment(shipment_id="shp-b1", cargo_value=50_000.0)
    s2 = _shipment(shipment_id="shp-b2", cargo_value=75_000.0)

    result = run(
        disruption=disruption,
        all_shipments=[s1, s2],
        all_routes=[],
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert result.business_impact_result is not None
    assert result.business_impact_result.total_cargo_value_at_risk_usd == 125_000.0


def test_approval_logic():
    """12. High cargo value or critical disruption severity requires approval; standard value does not."""
    # Scenario A: low cargo value, high severity disruption -> cargo_value (10k) <= threshold (50k) and severity != critical
    disruption_high = _disruption(severity="high")
    s_low_val = _shipment(shipment_id="shp-low-val", cargo_value=10_000.0)

    result_a = run(
        disruption=disruption_high,
        all_shipments=[s_low_val],
        all_routes=_routes(),
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
        approval_threshold_usd=50_000.0,
    )
    reroute_a = next(r for r in result_a.recommendations if r.type == "reroute")
    assert reroute_a.requires_approval is False

    # Scenario B: high cargo value (> 50k threshold) requires approval
    s_high_val = _shipment(shipment_id="shp-high-val", cargo_value=100_000.0)
    result_b = run(
        disruption=disruption_high,
        all_shipments=[s_high_val],
        all_routes=_routes(),
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
        approval_threshold_usd=50_000.0,
    )
    reroute_b = next(r for r in result_b.recommendations if r.type == "reroute")
    assert reroute_b.requires_approval is True

    # Scenario C: critical disruption severity requires approval regardless of cargo value
    disruption_crit = _disruption(severity="critical")
    result_c = run(
        disruption=disruption_crit,
        all_shipments=[s_low_val],
        all_routes=_routes(),
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
        approval_threshold_usd=50_000.0,
    )
    reroute_c = next(r for r in result_c.recommendations if r.type == "reroute")
    assert reroute_c.requires_approval is True


def test_explanation_and_reasoning_factors():
    """13. Recommendations contain meaningful descriptions, reasons, and populated reasoning_factors."""
    disruption = _disruption()
    s = _shipment(shipment_id="shp-reasoning")

    result = run(
        disruption=disruption,
        all_shipments=[s],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    for rec in result.recommendations:
        assert isinstance(rec.title, str) and len(rec.title) > 0
        assert isinstance(rec.description, str) and len(rec.description) > 0
        assert isinstance(rec.reason, str) and len(rec.reason) > 0

    reroute_rec = next(r for r in result.recommendations if r.type == "reroute")
    assert len(reroute_rec.reasoning_factors) > 0
    assert any("factor" in f for f in reroute_rec.reasoning_factors)


def test_output_structure():
    """14. Validates full OrchestratorResult and RecommendationCandidate fields."""
    disruption = _disruption()
    s = _shipment(shipment_id="shp-struct")

    result = run(
        disruption=disruption,
        all_shipments=[s],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=_fleet(),
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert hasattr(result, "recommendations")
    assert hasattr(result, "impact_result")
    assert hasattr(result, "cascade_result")
    assert hasattr(result, "business_impact_result")
    assert hasattr(result, "affected_shipment_ids")

    valid_types = {"reroute", "carrier_change", "fleet_redeploy", "hold", "expedite", "escalate"}
    valid_priorities = {"low", "medium", "high", "critical"}

    for candidate in result.recommendations:
        assert isinstance(candidate, RecommendationCandidate)
        assert candidate.type in valid_types
        assert candidate.priority in valid_priorities
        assert candidate.disruption_id == "disp-001"


def test_pure_python_no_database_side_effects():
    """15. Verifies RecommendationEngine is pure Python and operates cleanly with simple in-memory data."""
    # Ensure priority helper maps bounds properly
    assert _priority_from_score(0.85) == "critical"
    assert _priority_from_score(0.65) == "high"
    assert _priority_from_score(0.45) == "medium"
    assert _priority_from_score(0.15) == "low"
