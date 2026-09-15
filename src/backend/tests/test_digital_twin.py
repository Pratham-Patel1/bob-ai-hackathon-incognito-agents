"""
Tests for DigitalTwinEngine (in-memory what-if scenario simulation).
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch
import pytest

from backend.engines.digital_twin import (
    SimulationResult,
    SimulationSummary,
    run,
)
from backend.engines.predictive_risk import MLRiskResult, FeatureContribution
from backend.engines.shipment_risk import RiskResult


def _scenario(**kwargs: Any) -> dict[str, Any]:
    base = {
        "name": "Typhoon Simulation Scenario",
        "disruption_type": "weather",
        "severity": "high",
        "epicenter_lat": 22.0,
        "epicenter_lng": 114.0,
        "affected_radius_km": 300.0,
        "affected_route_codes": ["RT-HK-SGP"],
        "affected_region": "south china sea",
        "horizon_hours": 48.0,
    }
    base.update(kwargs)
    return base


def _shipment(
    shipment_id: str = "shp-001",
    status: str = "in_transit",
    lat: float = 22.2,
    lng: float = 114.1,
    route_code: str = "RT-HK-SGP",
    route_id: str = "r-curr",
    origin: str = "Hong Kong",
    destination: str = "Singapore",
    cargo_value: float = 60_000.0,
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
        "scheduled_departure": (now - timedelta(days=1)).isoformat(),
        "scheduled_arrival": (now + timedelta(days=2)).isoformat(),
        "estimated_arrival": (now + timedelta(days=3)).isoformat(),
        "weight_kg": 4000.0,
        "route_reliability_score": 0.85,
    }
    base.update(kwargs)
    return base


def _routes() -> list[dict[str, Any]]:
    return [
        {
            "id": "r-alt-1",
            "code": "RT-PACIFIC",
            "name": "Pacific Bypass Route",
            "origin": "Hong Kong",
            "destination": "Singapore",
            "active": True,
            "reliability_score": 0.92,
            "distance_km": 3500.0,
            "cost_per_kg_usd": 1.1,
            "typical_duration_hours": 48.0,
        }
    ]


def _carriers() -> list[dict[str, Any]]:
    return [
        {
            "id": "c-alt-1",
            "name": "Pacific Express Line",
            "code": "PEL-01",
            "reliability_score": 0.90,
            "cost_index": 0.95,
            "coverage_regions": ["singapore", "asia"],
            "active": True,
        }
    ]


def _carriers_by_id() -> dict[str, dict[str, Any]]:
    return {
        "c-curr": {
            "id": "c-curr",
            "name": "Current Carrier Line",
            "code": "CCL-01",
            "reliability_score": 0.75,
            "cost_index": 1.0,
            "coverage_regions": ["south china sea"],
            "active": True,
        }
    }


def _fleet() -> list[dict[str, Any]]:
    return [
        {
            "id": "f-001",
            "vehicle_id": "VH-IDLE-01",
            "status": "active",
            "utilization_pct": 15.0,
            "current_lat": 22.3,
            "current_lng": 114.2,
            "capacity_kg": 8000.0,
            "temperature_capable": True,
            "type": "feeder_vessel",
        }
    ]


def test_basic_simulation():
    """1. Basic simulation runs successfully and returns SimulationResult with SimulationSummary."""
    scenario = _scenario()
    shipment = _shipment()

    result = run(
        scenario=scenario,
        all_shipments=[shipment],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=_fleet(),
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert isinstance(result, SimulationResult)
    assert isinstance(result.summary, SimulationSummary)
    assert result.summary.scenario_name == "Typhoon Simulation Scenario"
    assert result.summary.total_affected_shipments == 1


def test_hypothetical_disruption_is_used():
    """2. Disruption supplied to the simulation is used without requiring DB existence."""
    scenario = _scenario(
        name="Custom Port Closure",
        disruption_type="port_closure",
        severity="critical",
        affected_radius_km=450.0,
        horizon_hours=96.0,
    )
    shipment = _shipment()

    result = run(
        scenario=scenario,
        all_shipments=[shipment],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert result.summary.scenario_name == "Custom Port Closure"
    assert result.summary.disruption_type == "port_closure"
    assert result.summary.disruption_severity == "critical"
    assert result.summary.affected_radius_km == 450.0
    assert result.summary.horizon_hours == 96.0


def test_pure_in_memory_no_database_side_effects():
    """3. Verify engine operates purely in-memory without PostgreSQL or SQLAlchemy dependencies."""
    scenario = _scenario()
    shipments = [_shipment()]

    # Verify run completes without any DB session or connection arguments
    result = run(
        scenario=scenario,
        all_shipments=shipments,
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=_fleet(),
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )
    assert result is not None


def test_input_data_is_not_mutated():
    """4. Verify input shipment and scenario dictionaries are not mutated by the simulation."""
    scenario = _scenario()
    shipments = [_shipment(shipment_id="shp-immut-1"), _shipment(shipment_id="shp-immut-2")]
    routes = _routes()
    carriers = _carriers()
    fleet = _fleet()

    scenario_copy = copy.deepcopy(scenario)
    shipments_copy = copy.deepcopy(shipments)
    routes_copy = copy.deepcopy(routes)
    carriers_copy = copy.deepcopy(carriers)
    fleet_copy = copy.deepcopy(fleet)

    run(
        scenario=scenario,
        all_shipments=shipments,
        all_routes=routes,
        all_carriers=carriers,
        all_fleet=fleet,
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert scenario == scenario_copy
    assert shipments == shipments_copy
    assert routes == routes_copy
    assert carriers == carriers_copy
    assert fleet == fleet_copy


def test_recommendation_integration():
    """5. Simulation invokes recommendation pipeline and returns recommendations for affected shipments."""
    scenario = _scenario()
    shipment = _shipment(cargo_value=80_000.0)

    result = run(
        scenario=scenario,
        all_shipments=[shipment],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=_fleet(),
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert len(result.top_recommendations) > 0
    assert result.summary.recommendation_count > 0
    types = [r["type"] for r in result.top_recommendations]
    assert "reroute" in types


def test_combined_risk_scoring():
    """6. Combined risk preserves the 0.6 deterministic + 0.4 ML policy and graceful fallback."""
    scenario = _scenario()
    shipment = _shipment(shipment_id="shp-risk-comb")

    # Mock ML and deterministic engines to verify arithmetic
    mock_ml = MLRiskResult(ml_score=0.75, top_features=[FeatureContribution("days", 2.0, 0.4)], model_version="v1")
    with patch("backend.engines.predictive_risk.run", return_value=mock_ml):
        with patch("backend.engines.shipment_risk.run") as mock_det:
            mock_det.return_value = RiskResult(score=0.50, level="medium", factors=[], explanation="ok")
            result = run(
                scenario=scenario,
                all_shipments=[shipment],
                all_routes=_routes(),
                all_carriers=_carriers(),
                all_fleet=[],
                temperature_excursions={},
                carriers_by_id=_carriers_by_id(),
            )
            # combined = 0.6 * 0.50 + 0.4 * 0.75 = 0.30 + 0.30 = 0.60
            assert "shp-risk-comb" in result.risk_scores
            assert pytest.approx(result.risk_scores["shp-risk-comb"], abs=1e-3) == 0.60


def test_affected_shipments_summary():
    """7. Affected shipment summaries contain expected fields and correct counts."""
    scenario = _scenario()
    s1 = _shipment(shipment_id="shp-aff-1")
    s2 = _shipment(shipment_id="shp-aff-2")

    result = run(
        scenario=scenario,
        all_shipments=[s1, s2],
        all_routes=[],
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert result.summary.total_affected_shipments == 2
    assert len(result.affected_shipments) == 2
    for item in result.affected_shipments:
        assert "shipment_id" in item
        assert "tracking_number" in item
        assert "combined_risk_score" in item
        assert isinstance(item["combined_risk_score"], float)


def test_cascade_impact_in_simulation():
    """8. Cascade results are captured and represented in summary and cascade_analysis."""
    scenario = _scenario()
    s1_direct = _shipment(shipment_id="shp-direct", lat=22.0, lng=114.0, fleet_id="f-shared")
    s2_secondary = _shipment(
        shipment_id="shp-secondary",
        lat=-10.0,
        lng=-10.0,
        route_code="RT-OTHER",
        fleet_id="f-shared",
        cargo_value=120_000.0,
    )

    result = run(
        scenario=scenario,
        all_shipments=[s1_direct, s2_secondary],
        all_routes=[],
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert result.cascade_analysis is not None
    assert result.summary.total_secondary_shipments == 1
    assert result.cascade_analysis.secondary_count == 1


def test_business_impact_in_simulation():
    """9. Business impact is computed and populated into simulation results and summary."""
    scenario = _scenario()
    s1 = _shipment(shipment_id="shp-biz-1", cargo_value=100_000.0)
    s2 = _shipment(shipment_id="shp-biz-2", cargo_value=50_000.0)

    result = run(
        scenario=scenario,
        all_shipments=[s1, s2],
        all_routes=[],
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert result.business_impact is not None
    assert result.summary.total_cargo_value_at_risk_usd == 150_000.0
    assert result.summary.total_cost_of_delay_usd == result.business_impact.cost_of_delay_usd
    assert result.summary.penalty_exposure_usd == result.business_impact.penalty_exposure_usd
    assert result.summary.sla_breach_count == result.business_impact.sla_breach_count


def test_recommendation_serialization():
    """10. Top recommendations are properly serialized dictionaries ready for API response."""
    scenario = _scenario()
    shipment = _shipment(cargo_value=75_000.0)

    result = run(
        scenario=scenario,
        all_shipments=[shipment],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=_fleet(),
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    for rec in result.top_recommendations:
        assert isinstance(rec, dict)
        assert "type" in rec
        assert "priority" in rec
        assert "title" in rec
        assert "reason" in rec
        assert "requires_approval" in rec
        assert "estimated_savings_usd" in rec
        assert isinstance(rec["requires_approval"], bool)
        assert isinstance(rec["estimated_savings_usd"], float)


def test_empty_and_no_impact_scenario():
    """11. Simulation does not crash when no shipments are affected or shipment list is empty."""
    scenario = _scenario()

    # Case A: empty shipment list
    result_empty = run(
        scenario=scenario,
        all_shipments=[],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )
    assert result_empty.summary.total_affected_shipments == 0
    assert result_empty.affected_shipments == []
    assert result_empty.top_recommendations == []

    # Case B: shipments exist but outside disruption radius
    s_far = _shipment(shipment_id="shp-far", lat=-50.0, lng=-50.0, route_code="RT-UNBLOCKED")
    result_no_impact = run(
        scenario=scenario,
        all_shipments=[s_far],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )
    assert result_no_impact.summary.total_affected_shipments == 0
    assert result_no_impact.affected_shipments == []
    assert result_no_impact.top_recommendations == []


def test_multiple_affected_shipments():
    """12. Multiple affected shipments are tracked and scored."""
    scenario = _scenario(epicenter_lat=22.0, epicenter_lng=114.0, affected_radius_km=500.0)
    s1 = _shipment(shipment_id="shp-m1", lat=22.1, lng=114.1)
    s2 = _shipment(shipment_id="shp-m2", lat=22.3, lng=114.3)
    s3 = _shipment(shipment_id="shp-m3", lat=22.4, lng=114.2)

    result = run(
        scenario=scenario,
        all_shipments=[s1, s2, s3],
        all_routes=[],
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    assert result.summary.total_affected_shipments == 3
    assert len(result.affected_shipments) == 3
    assert set(result.risk_scores.keys()) == {"shp-m1", "shp-m2", "shp-m3"}


def test_result_structure_and_types():
    """13. SimulationSummary and SimulationResult dataclass fields and types are strictly populated."""
    scenario = _scenario()
    shipment = _shipment()

    result = run(
        scenario=scenario,
        all_shipments=[shipment],
        all_routes=_routes(),
        all_carriers=_carriers(),
        all_fleet=_fleet(),
        temperature_excursions={},
        carriers_by_id=_carriers_by_id(),
    )

    summary = result.summary
    assert isinstance(summary.scenario_name, str)
    assert isinstance(summary.disruption_type, str)
    assert isinstance(summary.disruption_severity, str)
    assert isinstance(summary.affected_radius_km, float)
    assert isinstance(summary.horizon_hours, float)
    assert isinstance(summary.total_affected_shipments, int)
    assert isinstance(summary.total_secondary_shipments, int)
    assert isinstance(summary.total_cargo_value_at_risk_usd, float)
    assert isinstance(summary.total_cost_of_delay_usd, float)
    assert isinstance(summary.penalty_exposure_usd, float)
    assert isinstance(summary.sla_breach_count, int)
    assert isinstance(summary.recommendation_count, int)


def test_invalid_minimal_scenario_input():
    """14. Minimal or default scenario dictionary fails gracefully and applies fallback defaults."""
    minimal_scenario: dict[str, Any] = {}

    result = run(
        scenario=minimal_scenario,
        all_shipments=[],
        all_routes=[],
        all_carriers=[],
        all_fleet=[],
        temperature_excursions={},
        carriers_by_id={},
    )

    assert isinstance(result, SimulationResult)
    assert result.summary.scenario_name == "Unnamed"
    assert result.summary.disruption_type == "weather"
    assert result.summary.disruption_severity == "high"
    assert result.summary.horizon_hours == 72.0
    assert result.summary.affected_radius_km == 100.0
    assert result.summary.total_affected_shipments == 0
