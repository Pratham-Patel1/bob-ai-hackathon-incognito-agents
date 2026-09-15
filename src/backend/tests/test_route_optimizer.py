"""
Tests for RouteOptimizationEngine.
"""
from __future__ import annotations

from typing import Any
import pytest

from backend.engines.route_optimizer import (
    RouteOption,
    _location_matches,
    run,
)


def _shipment(**kwargs: Any) -> dict[str, Any]:
    base = {
        "origin": "Shanghai",
        "destination": "Rotterdam",
        "weight_kg": 2000.0,
        "temperature_required": False,
        "route_id": "r-current",
    }
    base.update(kwargs)
    return base


def _route(
    route_id: str = "r-alt-1",
    code: str = "RT-001",
    name: str = "Suez Canal Express",
    origin: str = "Shanghai",
    destination: str = "Rotterdam",
    **kwargs: Any,
) -> dict[str, Any]:
    base = {
        "id": route_id,
        "code": code,
        "name": name,
        "origin": origin,
        "destination": destination,
        "mode": "sea",
        "distance_km": 12000.0,
        "typical_duration_hours": 72.0,
        "cost_per_kg_usd": 1.5,
        "reliability_score": 0.85,
        "active": True,
    }
    base.update(kwargs)
    return base


def test_returns_valid_alternative_routes_for_matching_locations():
    """1. Returns valid alternative routes for matching origin/destination."""
    shipment = _shipment(origin="Shanghai", destination="Rotterdam")
    routes = [
        _route(route_id="r-1", code="RT-001", origin="Shanghai", destination="Rotterdam"),
        _route(route_id="r-2", code="RT-002", origin="Tokyo", destination="Los Angeles"),
    ]

    results = run(shipment, active_disruptions=[], available_routes=routes)

    assert len(results) == 1
    assert results[0].route_id == "r-1"
    assert results[0].route_code == "RT-001"


def test_excludes_current_route():
    """2. Excludes the shipment's current route."""
    shipment = _shipment(route_id="r-current")
    routes = [
        _route(route_id="r-current", code="RT-CURR"),
        _route(route_id="r-alt", code="RT-ALT"),
    ]

    results = run(shipment, active_disruptions=[], available_routes=routes)

    assert len(results) == 1
    assert results[0].route_id == "r-alt"
    assert results[0].route_code == "RT-ALT"


def test_excludes_inactive_routes():
    """3. Excludes inactive routes."""
    shipment = _shipment()
    routes = [
        _route(route_id="r-inactive", code="RT-INACTIVE", active=False),
        _route(route_id="r-active", code="RT-ACTIVE", active=True),
    ]

    results = run(shipment, active_disruptions=[], available_routes=routes)

    assert len(results) == 1
    assert results[0].route_id == "r-active"


def test_disruption_free_routes_receive_bonus_and_preferred():
    """4. Routes avoiding all active disruptions receive disruption bonus / are preferred."""
    shipment = _shipment()
    disruptions = [{"affected_route_codes": ["RT-BLOCKED"]}]
    routes = [
        _route(route_id="r-blocked", code="RT-BLOCKED", reliability_score=0.80),
        _route(route_id="r-free", code="RT-FREE", reliability_score=0.80),
    ]

    results = run(shipment, active_disruptions=disruptions, available_routes=routes)

    assert len(results) == 2
    free_route = next(r for r in results if r.route_code == "RT-FREE")
    blocked_route = next(r for r in results if r.route_code == "RT-BLOCKED")

    assert free_route.avoids_all_disruptions is True
    assert blocked_route.avoids_all_disruptions is False
    # Free route receives +0.2 bonus compared to the blocked route with identical stats
    assert pytest.approx(free_route.score - blocked_route.score, rel=1e-3) == 0.2


def test_affected_routes_still_returned_when_valid():
    """5. Routes affected by a disruption are still returned when they are otherwise valid."""
    shipment = _shipment()
    disruptions = [{"affected_route_codes": ["RT-DISRUPTED"]}]
    routes = [_route(route_id="r-1", code="RT-DISRUPTED")]

    results = run(shipment, active_disruptions=disruptions, available_routes=routes)

    assert len(results) == 1
    assert results[0].route_code == "RT-DISRUPTED"
    assert results[0].avoids_all_disruptions is False


def test_routes_sorted_disruption_free_first_then_score_descending():
    """6. Routes are sorted with disruption-free routes first, then by score descending."""
    shipment = _shipment()
    disruptions = [{"affected_route_codes": ["RT-AFFECTED"]}]

    # Route A: affected by disruption, but high base reliability
    route_a = _route(route_id="r-a", code="RT-AFFECTED", reliability_score=0.99)
    # Route B: disruption-free, lower reliability
    route_b = _route(route_id="r-b", code="RT-FREE-LOW", reliability_score=0.70)
    # Route C: disruption-free, higher reliability
    route_c = _route(route_id="r-c", code="RT-FREE-HIGH", reliability_score=0.90)

    results = run(
        shipment,
        active_disruptions=disruptions,
        available_routes=[route_a, route_b, route_c],
        top_n=5,
    )

    # Disruption-free routes come first, sorted by score descending: C, then B, then affected A
    assert len(results) == 3
    assert results[0].route_code == "RT-FREE-HIGH"
    assert results[1].route_code == "RT-FREE-LOW"
    assert results[2].route_code == "RT-AFFECTED"


def test_estimated_cost_equals_weight_times_cost_per_kg():
    """7. Estimated cost equals weight_kg * cost_per_kg_usd."""
    shipment = _shipment(weight_kg=2500.0)
    routes = [_route(cost_per_kg_usd=1.20)]

    results = run(shipment, active_disruptions=[], available_routes=routes)

    assert len(results) == 1
    expected_cost = 2500.0 * 1.20  # 3000.0
    assert results[0].estimated_cost_usd == pytest.approx(expected_cost, rel=1e-3)


def test_top_n_limits_returned_routes():
    """8. top_n limits the number of returned routes."""
    shipment = _shipment()
    routes = [
        _route(route_id=f"r-{i}", code=f"RT-{i}", reliability_score=0.5 + (i * 0.05))
        for i in range(5)
    ]

    results_top2 = run(shipment, active_disruptions=[], available_routes=routes, top_n=2)
    assert len(results_top2) == 2

    results_top4 = run(shipment, active_disruptions=[], available_routes=routes, top_n=4)
    assert len(results_top4) == 4


def test_returns_empty_list_when_no_alternative_route_exists():
    """9. Returns an empty list when no alternative route exists."""
    shipment = _shipment(origin="Berlin", destination="Munich", route_id="r-1")

    # Case A: available_routes is empty
    assert run(shipment, active_disruptions=[], available_routes=[]) == []

    # Case B: routes don't match origin/destination
    mismatched_routes = [_route(origin="Tokyo", destination="Sydney")]
    assert run(shipment, active_disruptions=[], available_routes=mismatched_routes) == []

    # Case C: only matching route is current route or inactive
    only_current_and_inactive = [
        _route(route_id="r-1", origin="Berlin", destination="Munich"),
        _route(route_id="r-2", origin="Berlin", destination="Munich", active=False),
    ]
    assert run(shipment, active_disruptions=[], available_routes=only_current_and_inactive) == []


def test_handles_multiple_active_disruptions():
    """10. Handles multiple active disruptions properly."""
    shipment = _shipment()
    disruptions = [
        {"affected_route_codes": ["RT-001", "RT-002"]},
        {"affected_route_codes": ["RT-003"]},
    ]
    routes = [
        _route(route_id="r-1", code="RT-001"),
        _route(route_id="r-2", code="RT-002"),
        _route(route_id="r-3", code="RT-003"),
        _route(route_id="r-4", code="RT-004"),  # Only this one is unblocked
    ]

    results = run(shipment, active_disruptions=disruptions, available_routes=routes, top_n=10)

    assert len(results) == 4
    route_map = {r.route_code: r for r in results}
    assert route_map["RT-004"].avoids_all_disruptions is True
    assert route_map["RT-001"].avoids_all_disruptions is False
    assert route_map["RT-002"].avoids_all_disruptions is False
    assert route_map["RT-003"].avoids_all_disruptions is False


def test_location_matching_behavior():
    """11. Test flexible location matching behavior."""
    # Direct function checks
    assert _location_matches("shanghai", "shanghai") is True       # exact
    assert _location_matches("shanghai port", "shanghai") is True  # prefix / substring
    assert _location_matches("rotterdam hub", "rotterdam") is True
    assert _location_matches("port of los angeles", "los angeles") is True  # substring
    assert _location_matches("", "shanghai") is False              # empty route loc
    assert _location_matches("shanghai", "") is False              # empty shipment loc
    assert _location_matches("tokyo", "singapore") is False        # mismatch

    # End-to-end run matching check with case/spacing insensitivity
    shipment = _shipment(origin="  SHANGHAI  ", destination="Rotterdam Port")
    route = _route(origin="Shanghai Central", destination="Rotterdam")
    results = run(shipment, active_disruptions=[], available_routes=[route])
    assert len(results) == 1


def test_route_option_fields_populated_correctly():
    """12. Verify returned RouteOption fields and reason are populated correctly."""
    shipment = _shipment(
        weight_kg=1500.0,
        temperature_required=True,
    )
    route = _route(
        route_id="r-99",
        code="RT-TEST",
        name="Northern Corridor",
        typical_duration_hours=42.5,
        cost_per_kg_usd=2.0,
        reliability_score=0.92,
    )

    results = run(shipment, active_disruptions=[], available_routes=[route])

    assert len(results) == 1
    opt = results[0]
    assert isinstance(opt, RouteOption)
    assert opt.route_id == "r-99"
    assert opt.route_code == "RT-TEST"
    assert opt.route_name == "Northern Corridor"
    assert isinstance(opt.score, float)
    assert opt.score > 0.0
    assert opt.estimated_duration_hours == 42.5
    assert opt.estimated_cost_usd == 3000.0
    assert opt.avoids_all_disruptions is True
    assert "RT-TEST" in opt.reason
    assert "avoids all active disruption zones" in opt.reason
    assert "temperature-capable" in opt.reason
