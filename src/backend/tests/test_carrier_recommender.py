"""
Tests for CarrierRecommendationEngine — Phase 2D

Run with:
    pytest src/backend/tests/test_carrier_recommender.py -v
"""

from __future__ import annotations

import pytest

from backend.engines.carrier_recommender import (
    CarrierRecommendationResult,
    RankedCarrier,
    WEIGHT_ON_TIME,
    WEIGHT_COST,
    WEIGHT_CAPACITY,
    WEIGHT_BUSYNESS,
    recommend_carriers,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _carrier(
    id: str = "C001",
    name: str = "FastShip Logistics",
    carrier_code: str = "FSL",
    on_time_rate: float = 0.92,
    available_capacity: float = 20.0,
    spot_rate_usd_per_km: float = 2.5,
    active_shipments: int = 5,
    max_shipments: int = 20,
    has_reefer: bool = False,
    reliability_score: float = 0.92,
) -> dict:
    return {
        "id": id,
        "name": name,
        "carrier_code": carrier_code,
        "on_time_rate": on_time_rate,
        "available_capacity": available_capacity,
        "spot_rate_usd_per_km": spot_rate_usd_per_km,
        "active_shipments": active_shipments,
        "max_shipments": max_shipments,
        "has_reefer": has_reefer,
        "reliability_score": reliability_score,
    }


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

class TestEmptyInput:
    def test_empty_carriers_returns_result(self):
        result = recommend_carriers([])
        assert isinstance(result, CarrierRecommendationResult)
        assert result.recommended_carrier is None

    def test_empty_carriers_mentions_no_carriers(self):
        result = recommend_carriers([])
        assert any("No carriers" in f for f in result.factors)


# ---------------------------------------------------------------------------
# Single carrier
# ---------------------------------------------------------------------------

class TestSingleCarrier:
    def test_single_carrier_recommended(self):
        result = recommend_carriers([_carrier()])
        assert result.recommended_carrier is not None
        assert result.recommended_carrier.id == "C001"

    def test_single_carrier_rank_is_1(self):
        result = recommend_carriers([_carrier()])
        assert result.ranked_carriers[0].rank == 1


# ---------------------------------------------------------------------------
# Reefer matching
# ---------------------------------------------------------------------------

class TestReeferMatching:
    def test_non_reefer_carrier_ineligible_when_reefer_required(self):
        carriers = [_carrier(has_reefer=False)]
        result = recommend_carriers(carriers, {"requires_reefer": True})
        assert result.ranked_carriers[0].reefer_eligible is False

    def test_reefer_carrier_eligible_when_reefer_required(self):
        carriers = [_carrier(has_reefer=True)]
        result = recommend_carriers(carriers, {"requires_reefer": True})
        assert result.ranked_carriers[0].reefer_eligible is True

    def test_reefer_carrier_preferred_over_non_reefer(self):
        carriers = [
            _carrier(id="C1", name="NoReefer", has_reefer=False, on_time_rate=0.95),
            _carrier(id="C2", name="Reefer",   has_reefer=True,  on_time_rate=0.85),
        ]
        result = recommend_carriers(carriers, {"requires_reefer": True})
        assert result.recommended_carrier.name == "Reefer"

    def test_all_carriers_eligible_when_no_reefer_needed(self):
        carriers = [
            _carrier(id="C1", has_reefer=False),
            _carrier(id="C2", has_reefer=True),
        ]
        result = recommend_carriers(carriers, {"requires_reefer": False})
        assert all(c.reefer_eligible for c in result.ranked_carriers)


# ---------------------------------------------------------------------------
# Capacity matching
# ---------------------------------------------------------------------------

class TestCapacityMatching:
    def test_insufficient_capacity_reduces_score(self):
        carriers = [
            _carrier(id="C1", name="Small", available_capacity=2.0),
            _carrier(id="C2", name="Large", available_capacity=50.0),
        ]
        result = recommend_carriers(carriers, {"required_capacity": 10.0})
        assert result.recommended_carrier.name == "Large"

    def test_zero_capacity_carrier_penalised(self):
        carriers = [
            _carrier(id="C1", available_capacity=0.0),
            _carrier(id="C2", available_capacity=20.0),
        ]
        result = recommend_carriers(carriers, {"required_capacity": 5.0})
        assert result.recommended_carrier.id == "C2"


# ---------------------------------------------------------------------------
# On-time rate ranking
# ---------------------------------------------------------------------------

class TestOnTimeRanking:
    def test_higher_on_time_rate_ranks_higher(self):
        carriers = [
            _carrier(id="C1", name="Reliable",  on_time_rate=0.97, spot_rate_usd_per_km=3.0),
            _carrier(id="C2", name="Unreliable", on_time_rate=0.60, spot_rate_usd_per_km=3.0),
        ]
        result = recommend_carriers(carriers)
        assert result.recommended_carrier.name == "Reliable"

    def test_on_time_score_proportional(self):
        c = _carrier(on_time_rate=0.85)
        result = recommend_carriers([c])
        assert result.ranked_carriers[0].on_time_score == pytest.approx(85.0)


# ---------------------------------------------------------------------------
# Cost scoring
# ---------------------------------------------------------------------------

class TestCostScoring:
    def test_lower_spot_rate_preferred_when_other_factors_equal(self):
        carriers = [
            _carrier(id="C1", name="Cheap",     spot_rate_usd_per_km=1.0),
            _carrier(id="C2", name="Expensive", spot_rate_usd_per_km=5.0),
        ]
        result = recommend_carriers(carriers, {"required_capacity": 10.0})
        assert result.recommended_carrier.name == "Cheap"

    def test_estimated_cost_calculated_correctly(self):
        c = _carrier(spot_rate_usd_per_km=2.0)
        result = recommend_carriers([c], {"route_distance_km": 500.0})
        assert result.ranked_carriers[0].estimated_cost_usd == pytest.approx(1000.0)


# ---------------------------------------------------------------------------
# Busyness scoring
# ---------------------------------------------------------------------------

class TestBusynessScoring:
    def test_fully_busy_carrier_has_low_busyness_score(self):
        c = _carrier(active_shipments=20, max_shipments=20)
        result = recommend_carriers([c])
        assert result.ranked_carriers[0].busyness_score == pytest.approx(0.0)

    def test_idle_carrier_has_high_busyness_score(self):
        c = _carrier(active_shipments=0, max_shipments=20)
        result = recommend_carriers([c])
        assert result.ranked_carriers[0].busyness_score == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# Priority thresholds
# ---------------------------------------------------------------------------

class TestPriorityThresholds:
    def test_critical_priority_sets_high_min_reliability(self):
        """Only a high-reliability carrier should be recommended for CRITICAL."""
        carriers = [
            _carrier(id="C1", name="HighRel", reliability_score=0.95, available_capacity=10.0),
            _carrier(id="C2", name="LowRel",  reliability_score=0.50, available_capacity=10.0),
        ]
        result = recommend_carriers(carriers, {
            "shipment_priority": "critical",
            "required_capacity": 5.0,
        })
        assert result.recommended_carrier.name == "HighRel"


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_returns_correct_dataclass(self):
        result = recommend_carriers([_carrier()])
        assert isinstance(result, CarrierRecommendationResult)

    def test_ranked_carriers_list_of_ranked_carrier(self):
        result = recommend_carriers([_carrier(), _carrier(id="C2", carrier_code="XYZ")])
        for c in result.ranked_carriers:
            assert isinstance(c, RankedCarrier)

    def test_ranks_are_sequential(self):
        carriers = [_carrier(id=f"C{i}", carrier_code=f"C{i}") for i in range(4)]
        result = recommend_carriers(carriers)
        ranks = [c.rank for c in result.ranked_carriers]
        assert ranks == list(range(1, 5))

    def test_factors_list_of_strings(self):
        result = recommend_carriers([_carrier()])
        assert all(isinstance(f, str) for f in result.factors)

    def test_scores_in_valid_range(self):
        carriers = [
            _carrier(id="C1", on_time_rate=0.0, available_capacity=0.0),
            _carrier(id="C2", on_time_rate=1.0, available_capacity=100.0),
        ]
        result = recommend_carriers(carriers)
        for c in result.ranked_carriers:
            assert 0.0 <= c.on_time_score    <= 100.0
            assert 0.0 <= c.cost_score       <= 100.0
            assert 0.0 <= c.capacity_score   <= 100.0
            assert 0.0 <= c.busyness_score   <= 100.0
            assert 0.0 <= c.composite_score  <= 100.0

    def test_deterministic_same_input(self):
        carriers = [_carrier(), _carrier(id="C2", carrier_code="ZZZ", on_time_rate=0.75)]
        r1 = recommend_carriers(carriers)
        r2 = recommend_carriers(carriers)
        assert [c.rank for c in r1.ranked_carriers] == [c.rank for c in r2.ranked_carriers]
