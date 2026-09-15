"""
Tests for CarrierRecommendationEngine.
"""
from __future__ import annotations

from typing import Any
import pytest

from backend.engines.carrier_recommender import (
    CarrierOption,
    _covers_destination,
    run,
)


def _shipment(**kwargs: Any) -> dict[str, Any]:
    base = {
        "cargo_type": "general",
        "weight_kg": 2000.0,
        "temperature_required": False,
        "destination": "Rotterdam",
    }
    base.update(kwargs)
    return base


def _carrier(
    carrier_id: str = "c-1",
    name: str = "Pacific Logistics",
    code: str = "PAC-01",
    reliability_score: float = 0.85,
    cost_index: float = 1.0,
    coverage_regions: list[str] | None = None,
    active: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    if coverage_regions is None:
        coverage_regions = ["rotterdam", "europe", "global"]
    base = {
        "id": carrier_id,
        "name": name,
        "code": code,
        "reliability_score": reliability_score,
        "cost_index": cost_index,
        "coverage_regions": coverage_regions,
        "active": active,
    }
    base.update(kwargs)
    return base


def test_returns_valid_alternative_carriers():
    """1. Returns valid alternative carriers for a shipment."""
    shipment = _shipment(destination="Rotterdam")
    current_carrier = {"id": "c-curr"}
    all_carriers = [
        _carrier(carrier_id="c-alt-1", name="Carrier Alpha", code="CAR-A"),
        _carrier(carrier_id="c-alt-2", name="Carrier Beta", code="CAR-B"),
    ]

    results = run(shipment, current_carrier, all_carriers, active_disruptions=[])

    assert len(results) == 2
    assert {r.carrier_id for r in results} == {"c-alt-1", "c-alt-2"}


def test_excludes_current_carrier():
    """2. Excludes the current carrier from recommendations."""
    shipment = _shipment()
    current_carrier = {"id": "c-current"}
    all_carriers = [
        _carrier(carrier_id="c-current", name="Current Carrier"),
        _carrier(carrier_id="c-alt", name="Alternative Carrier"),
    ]

    results = run(shipment, current_carrier, all_carriers, active_disruptions=[])

    assert len(results) == 1
    assert results[0].carrier_id == "c-alt"


def test_excludes_inactive_carriers():
    """3. Excludes inactive carriers."""
    shipment = _shipment()
    current_carrier = {"id": "c-curr"}
    all_carriers = [
        _carrier(carrier_id="c-inactive", name="Inactive Carrier", active=False),
        _carrier(carrier_id="c-active", name="Active Carrier", active=True),
    ]

    results = run(shipment, current_carrier, all_carriers, active_disruptions=[])

    assert len(results) == 1
    assert results[0].carrier_id == "c-active"


def test_excludes_carriers_overlapping_disruption_region():
    """4. Excludes carriers whose coverage overlaps an active disruption region."""
    shipment = _shipment(destination="Rotterdam")
    current_carrier = {"id": "c-curr"}
    disruptions = [{"affected_region": "red sea"}]

    all_carriers = [
        _carrier(carrier_id="c-disrupted", coverage_regions=["red sea", "rotterdam"]),
        _carrier(carrier_id="c-safe", coverage_regions=["cape route", "rotterdam"]),
    ]

    results = run(shipment, current_carrier, all_carriers, active_disruptions=disruptions)

    assert len(results) == 1
    assert results[0].carrier_id == "c-safe"


def test_ranks_carriers_using_reliability_and_cost():
    """5. Ranks carriers using reliability and cost_index (score = reliability / cost_index)."""
    shipment = _shipment(destination="Rotterdam")
    current_carrier = {"id": "c-curr"}

    # Carrier A: rel=0.90, cost=1.00 -> score = 0.90
    # Carrier B: rel=0.80, cost=0.80 -> score = 1.00 (better value)
    carrier_a = _carrier(carrier_id="c-a", reliability_score=0.90, cost_index=1.00)
    carrier_b = _carrier(carrier_id="c-b", reliability_score=0.80, cost_index=0.80)

    results = run(shipment, current_carrier, [carrier_a, carrier_b], active_disruptions=[])

    assert len(results) == 2
    assert results[0].carrier_id == "c-b"
    assert results[0].score == 1.00
    assert results[1].carrier_id == "c-a"
    assert results[1].score == 0.90


def test_better_reliability_and_lower_cost_gets_higher_score():
    """6. A carrier with higher reliability and lower cost receives a strictly higher score."""
    shipment = _shipment(destination="Rotterdam")
    current_carrier = {"id": "c-curr"}

    carrier_premium = _carrier(carrier_id="c-prem", reliability_score=0.95, cost_index=0.85)
    carrier_budget = _carrier(carrier_id="c-budget", reliability_score=0.70, cost_index=1.20)

    results = run(shipment, current_carrier, [carrier_budget, carrier_premium], active_disruptions=[])

    assert len(results) == 2
    assert results[0].carrier_id == "c-prem"
    assert results[0].score > results[1].score


def test_destination_coverage_detection():
    """7. Destination coverage is detected correctly (exact match, substring in destination, 4-char prefix)."""
    # Direct function checks
    assert _covers_destination(["rotterdam", "apac"], "Rotterdam") is True
    assert _covers_destination(["rotterdam"], "Port of Rotterdam") is True
    assert _covers_destination(["rott"], "Rotterdam") is True
    assert _covers_destination(["singapore", "tokyo"], "Rotterdam") is False
    assert _covers_destination([], "Rotterdam") is False

    # Through engine run
    shipment = _shipment(destination="Hamburg Port")
    all_carriers = [
        _carrier(carrier_id="c-covers", coverage_regions=["hamburg"]),
        _carrier(carrier_id="c-no-cover", coverage_regions=["los angeles"]),
    ]

    results = run(shipment, {"id": "c-curr"}, all_carriers, active_disruptions=[])
    covered = next(r for r in results if r.carrier_id == "c-covers")
    not_covered = next(r for r in results if r.carrier_id == "c-no-cover")

    assert covered.covers_region is True
    assert not_covered.covers_region is False


def test_carriers_without_destination_coverage_receive_score_penalty():
    """8. Carriers without destination coverage can still be returned but receive a 0.6x score penalty."""
    shipment = _shipment(destination="Rotterdam")
    current_carrier = {"id": "c-curr"}

    # Both carriers have identical reliability and cost index
    carrier_covered = _carrier(carrier_id="c-cov", reliability_score=0.80, cost_index=1.0, coverage_regions=["rotterdam"])
    carrier_uncovered = _carrier(carrier_id="c-uncov", reliability_score=0.80, cost_index=1.0, coverage_regions=["sydney"])

    results = run(shipment, current_carrier, [carrier_covered, carrier_uncovered], active_disruptions=[])

    assert len(results) == 2
    cov = next(r for r in results if r.carrier_id == "c-cov")
    uncov = next(r for r in results if r.carrier_id == "c-uncov")

    assert cov.score == 0.80
    assert pytest.approx(uncov.score, rel=1e-3) == 0.80 * 0.6  # 0.48


def test_top_n_limits_returned_carriers():
    """9. top_n limits the number of returned carriers."""
    shipment = _shipment()
    current_carrier = {"id": "c-curr"}
    carriers = [
        _carrier(carrier_id=f"c-{i}", reliability_score=0.5 + (i * 0.05))
        for i in range(5)
    ]

    assert len(run(shipment, current_carrier, carriers, active_disruptions=[], top_n=2)) == 2
    assert len(run(shipment, current_carrier, carriers, active_disruptions=[], top_n=4)) == 4


def test_returns_empty_list_when_no_eligible_carriers_exist():
    """10. Returns an empty list when no eligible carriers exist."""
    shipment = _shipment()
    current_carrier = {"id": "c-curr"}

    # Case A: empty list of carriers
    assert run(shipment, current_carrier, [], active_disruptions=[]) == []

    # Case B: only current carrier or inactive carriers
    all_ineligible = [
        _carrier(carrier_id="c-curr"),
        _carrier(carrier_id="c-inactive", active=False),
    ]
    assert run(shipment, current_carrier, all_ineligible, active_disruptions=[]) == []

    # Case C: all carriers are in active disruption zones
    disrupted = [{"affected_region": "asia"}]
    all_disrupted = [
        _carrier(carrier_id="c-1", coverage_regions=["asia"]),
        _carrier(carrier_id="c-2", coverage_regions=["asia", "europe"]),
    ]
    assert run(shipment, current_carrier, all_disrupted, active_disruptions=disrupted) == []


def test_handles_multiple_active_disruptions():
    """11. Handles multiple active disruption regions accurately."""
    shipment = _shipment(destination="Rotterdam")
    current_carrier = {"id": "c-curr"}
    disruptions = [
        {"affected_region": "suez canal"},
        {"affected_region": "strait of malacca"},
        {"affected_region": ""},  # empty region should be handled gracefully
    ]
    carriers = [
        _carrier(carrier_id="c-blocked-1", coverage_regions=["suez canal"]),
        _carrier(carrier_id="c-blocked-2", coverage_regions=["strait of malacca"]),
        _carrier(carrier_id="c-safe", coverage_regions=["pacific", "rotterdam"]),
    ]

    results = run(shipment, current_carrier, carriers, active_disruptions=disruptions)

    assert len(results) == 1
    assert results[0].carrier_id == "c-safe"


def test_carrier_option_fields_and_explanation_populated():
    """12. Verify CarrierOption fields and reason string are populated correctly."""
    shipment = _shipment(destination="Rotterdam")
    current_carrier = {"id": "c-curr"}
    carrier = _carrier(
        carrier_id="c-100",
        name="Apex Global Shipping",
        code="APX-99",
        reliability_score=0.92,
        cost_index=0.85,
        coverage_regions=["rotterdam", "north sea"],
    )

    results = run(shipment, current_carrier, [carrier], active_disruptions=[])

    assert len(results) == 1
    opt = results[0]
    assert isinstance(opt, CarrierOption)
    assert opt.carrier_id == "c-100"
    assert opt.carrier_name == "Apex Global Shipping"
    assert opt.carrier_code == "APX-99"
    assert opt.reliability_score == 0.92
    assert opt.cost_index == 0.85
    assert opt.covers_region is True
    assert isinstance(opt.score, float)
    assert opt.score > 0.0

    # Verify explanation content
    assert "Apex Global Shipping" in opt.reason
    assert "0.92" in opt.reason
    assert "0.85" in opt.reason
    assert "covers Rotterdam region" in opt.reason
