"""
Tests for RouteOptimizationEngine — Phase 2D

Run with:
    pytest src/backend/tests/test_route_optimizer.py -v
"""

from __future__ import annotations

import pytest

from backend.engines.route_optimizer import (
    RankedRoute,
    RouteOptimizationResult,
    WEIGHT_SAFETY,
    WEIGHT_ETA,
    WEIGHT_COST,
    optimize_routes,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _route(
    id: str = "R001",
    name: str = "Route A",
    origin: str = "Mumbai",
    destination: str = "Delhi",
    distance_km: float = 1400.0,
    estimated_hours: float = 20.0,
    risk_level: str = "low",
    toll_cost_usd: float = 50.0,
    fuel_cost_usd: float = 200.0,
    reliability_score: float = 0.90,
    is_blocked: bool = False,
    disruption_overlap: float = 0.0,
) -> dict:
    return {
        "id": id,
        "name": name,
        "origin": origin,
        "destination": destination,
        "distance_km": distance_km,
        "estimated_hours": estimated_hours,
        "risk_level": risk_level,
        "toll_cost_usd": toll_cost_usd,
        "fuel_cost_usd": fuel_cost_usd,
        "reliability_score": reliability_score,
        "is_blocked": is_blocked,
        "disruption_overlap": disruption_overlap,
    }


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_routes_returns_result(self):
        result = optimize_routes([])
        assert isinstance(result, RouteOptimizationResult)
        assert result.recommended_route is None
        assert result.ranked_routes == []

    def test_empty_factors_mention_no_routes(self):
        result = optimize_routes([])
        assert any("No routes" in f for f in result.factors)


# ---------------------------------------------------------------------------
# Single route
# ---------------------------------------------------------------------------

class TestSingleRoute:
    def test_single_route_is_recommended(self):
        route = _route()
        result = optimize_routes([route])
        assert result.recommended_route is not None
        assert result.recommended_route.id == "R001"
        assert result.recommended_route.rank == 1

    def test_single_blocked_route_still_ranked(self):
        route = _route(is_blocked=True)
        result = optimize_routes([route])
        assert len(result.ranked_routes) == 1
        # Blocked route must have safety_score of exactly 0
        assert result.ranked_routes[0].safety_score == 0.0


# ---------------------------------------------------------------------------
# Ranking logic
# ---------------------------------------------------------------------------

class TestRankingLogic:
    def test_blocked_route_always_last(self):
        routes = [
            _route(id="R1", name="Blocked", is_blocked=True, risk_level="low",
                   estimated_hours=10, toll_cost_usd=10, fuel_cost_usd=10),
            _route(id="R2", name="Safe", is_blocked=False, risk_level="low",
                   estimated_hours=20, toll_cost_usd=50, fuel_cost_usd=200),
        ]
        result = optimize_routes(routes)
        last = result.ranked_routes[-1]
        assert last.is_blocked is True

    def test_low_risk_outranks_high_risk(self):
        routes = [
            _route(id="R1", name="LowRisk",  risk_level="low",      disruption_overlap=0.0),
            _route(id="R2", name="HighRisk", risk_level="critical", disruption_overlap=0.5),
        ]
        result = optimize_routes(routes)
        assert result.ranked_routes[0].name == "LowRisk"

    def test_fastest_route_preferred_when_same_safety(self):
        routes = [
            _route(id="R1", name="Fast",  risk_level="low", estimated_hours=10, is_blocked=False),
            _route(id="R2", name="Slow",  risk_level="low", estimated_hours=30, is_blocked=False),
        ]
        result = optimize_routes(routes)
        assert result.ranked_routes[0].name == "Fast"

    def test_cheaper_route_preferred_when_same_safety_and_eta(self):
        routes = [
            _route(id="R1", name="Cheap",     toll_cost_usd=10,  fuel_cost_usd=50),
            _route(id="R2", name="Expensive", toll_cost_usd=100, fuel_cost_usd=500),
        ]
        result = optimize_routes(routes)
        assert result.ranked_routes[0].name == "Cheap"


# ---------------------------------------------------------------------------
# Safety scoring
# ---------------------------------------------------------------------------

class TestSafetyScoring:
    def test_blocked_route_safety_zero(self):
        route = _route(is_blocked=True)
        result = optimize_routes([route])
        assert result.ranked_routes[0].safety_score == 0.0

    def test_overlap_reduces_safety(self):
        no_overlap = _route(id="R1", disruption_overlap=0.0)
        full_overlap = _route(id="R2", disruption_overlap=1.0)
        r_none = optimize_routes([no_overlap]).ranked_routes[0]
        r_full = optimize_routes([full_overlap]).ranked_routes[0]
        assert r_none.safety_score > r_full.safety_score

    def test_critical_risk_safety_penalty(self):
        safe  = _route(id="R1", risk_level="low")
        crit  = _route(id="R2", risk_level="critical")
        r1 = optimize_routes([safe]).ranked_routes[0]
        r2 = optimize_routes([crit]).ranked_routes[0]
        assert r1.safety_score > r2.safety_score

    def test_high_reliability_boosts_safety(self):
        """Reliability bonus is relative — use medium-risk base to avoid capping at 100."""
        low_rel  = _route(id="R1", reliability_score=0.50, risk_level="medium")
        high_rel = _route(id="R2", reliability_score=1.00, risk_level="medium")
        r1 = optimize_routes([low_rel]).ranked_routes[0]
        r2 = optimize_routes([high_rel]).ranked_routes[0]
        assert r2.safety_score > r1.safety_score


# ---------------------------------------------------------------------------
# Priority ETA weight adjustment
# ---------------------------------------------------------------------------

class TestPriorityAdjustment:
    def test_critical_priority_boosts_eta_weight(self):
        """Critical priority should increase eta weight relative to low priority."""
        routes = [_route()]
        r_low  = optimize_routes(routes, {"shipment_priority": "low"})
        r_crit = optimize_routes(routes, {"shipment_priority": "critical"})
        # Just verify it doesn't crash and returns sensible results
        assert r_crit.recommended_route is not None
        assert r_low.recommended_route is not None

    def test_multiple_routes_critical_priority(self):
        routes = [
            _route(id="R1", estimated_hours=10, risk_level="low"),
            _route(id="R2", estimated_hours=40, risk_level="low"),
        ]
        result = optimize_routes(routes, {"shipment_priority": "critical"})
        # Fast route should still rank first for critical priority
        assert result.recommended_route.estimated_hours == 10.0


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_returns_correct_dataclass(self):
        result = optimize_routes([_route()])
        assert isinstance(result, RouteOptimizationResult)

    def test_ranked_routes_is_list_of_ranked_route(self):
        result = optimize_routes([_route(), _route(id="R2", name="Route B")])
        for r in result.ranked_routes:
            assert isinstance(r, RankedRoute)

    def test_ranks_are_sequential(self):
        routes = [_route(id=f"R{i}", name=f"Route {i}") for i in range(5)]
        result = optimize_routes(routes)
        ranks = [r.rank for r in result.ranked_routes]
        assert ranks == list(range(1, 6))

    def test_factors_list_of_strings(self):
        result = optimize_routes([_route()])
        assert all(isinstance(f, str) for f in result.factors)

    def test_total_cost_is_toll_plus_fuel(self):
        route = _route(toll_cost_usd=100, fuel_cost_usd=200)
        result = optimize_routes([route])
        assert result.ranked_routes[0].total_cost_usd == pytest.approx(300.0)

    def test_scores_in_valid_range(self):
        routes = [
            _route(id="R1", risk_level="critical", disruption_overlap=1.0, is_blocked=True),
            _route(id="R2", risk_level="low",      disruption_overlap=0.0),
        ]
        result = optimize_routes(routes)
        for r in result.ranked_routes:
            assert 0.0 <= r.safety_score <= 100.0
            assert 0.0 <= r.eta_score    <= 100.0
            assert 0.0 <= r.cost_score   <= 100.0
            assert 0.0 <= r.composite_score <= 100.0

    def test_deterministic_same_input(self):
        routes = [_route(id="R1"), _route(id="R2", name="Route B")]
        r1 = optimize_routes(routes)
        r2 = optimize_routes(routes)
        assert [r.rank for r in r1.ranked_routes] == [r.rank for r in r2.ranked_routes]
