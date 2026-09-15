"""
Tests for DisruptionImpactEngine.
"""
from datetime import datetime, timedelta, timezone

import pytest
from backend.engines.disruption_impact import run, ImpactResult


def _make_disruption(**kwargs):
    base = {
        "id": "d1",
        "epicenter_lat": 53.5511,   # Hamburg
        "epicenter_lng": 9.9937,
        "affected_radius_km": 200.0,
        "affected_route_codes": ["R-01", "R-02"],
        "severity": "high",
    }
    base.update(kwargs)
    return base


def _make_shipment(**kwargs):
    base = {
        "id": "s1",
        "current_lat": 53.5511,   # Hamburg — inside radius
        "current_lng": 9.9937,
        "route_code": "R-99",
    }
    base.update(kwargs)
    return base


def _impact(disruption=None, shipment=None):
    """Return the single result for focused scoring assertions."""
    result = run(disruption or _make_disruption(), [shipment or _make_shipment()])
    assert result.affected_count == 1
    return result.impacted_shipments[0]


def test_geo_intersection_within_radius():
    disruption = _make_disruption()
    shipment = _make_shipment()  # at epicenter
    result = run(disruption, [shipment])
    assert result.affected_count == 1
    assert result.impacted_shipments[0].impact_reason in ("geo_intersection", "both")
    assert result.impacted_shipments[0].distance_to_epicenter_km is not None
    assert result.impacted_shipments[0].distance_to_epicenter_km < 1.0


def test_geo_outside_radius_not_affected():
    disruption = _make_disruption(affected_radius_km=50.0)
    # Tokyo is ~9,200 km from Hamburg
    shipment = _make_shipment(current_lat=35.6762, current_lng=139.6503, route_code="R-99")
    result = run(disruption, [shipment])
    assert result.affected_count == 0


def test_route_code_match():
    disruption = _make_disruption(affected_radius_km=1.0)  # tiny radius
    # Shipment in Tokyo (outside geo) but on blocked route
    shipment = _make_shipment(current_lat=35.6762, current_lng=139.6503, route_code="R-01")
    result = run(disruption, [shipment])
    assert result.affected_count == 1
    assert result.impacted_shipments[0].impact_reason == "route_blocked"


def test_both_geo_and_route():
    disruption = _make_disruption()
    shipment = _make_shipment(route_code="R-01")  # inside geo + on blocked route
    result = run(disruption, [shipment])
    assert result.affected_count == 1
    assert result.impacted_shipments[0].impact_reason == "both"


def test_empty_shipments():
    result = run(_make_disruption(), [])
    assert result.affected_count == 0
    assert result.impacted_shipments == []


def test_multiple_shipments_mixed():
    disruption = _make_disruption()
    shipments = [
        _make_shipment(id="s1"),               # inside geo
        _make_shipment(id="s2", current_lat=35.6762, current_lng=139.6503, route_code="R-99"),  # outside, no route
        _make_shipment(id="s3", current_lat=35.6762, current_lng=139.6503, route_code="R-02"),  # route match
    ]
    result = run(disruption, shipments)
    assert result.affected_count == 2
    ids = {i.shipment_id for i in result.impacted_shipments}
    assert "s1" in ids
    assert "s3" in ids
    assert "s2" not in ids


@pytest.mark.parametrize(
    ("severity", "expected_score", "expected_level"),
    [
        ("low", 30, "MEDIUM"),
        ("medium", 45, "MEDIUM"),
        ("high", 60, "HIGH"),
        ("critical", 75, "CRITICAL"),
    ],
)
def test_severity_contribution_and_level(severity, expected_score, expected_level):
    impacted = _impact(
        _make_disruption(severity=severity, affected_radius_km=1.0),
        _make_shipment(current_lat=35.6762, current_lng=139.6503, route_code="R-01"),
    )
    assert impacted.impact_score == expected_score
    assert impacted.impact_level == expected_level
    assert f"{severity.title()} severity disruption" in impacted.factors[0]


def test_geo_exposure_contribution():
    impacted = _impact(_make_disruption(severity="low"))
    assert impacted.impact_reason == "geo_intersection"
    assert "Shipment intersects disruption area (+10)" in impacted.factors
    assert impacted.impact_score == 35


def test_route_blocked_exposure_contribution():
    impacted = _impact(
        _make_disruption(severity="low", affected_radius_km=1.0),
        _make_shipment(current_lat=35.6762, current_lng=139.6503, route_code="R-01"),
    )
    assert impacted.impact_score == 30
    assert "Shipment route is directly blocked (+15)" in impacted.factors


def test_both_exposures_use_single_twenty_point_contribution():
    impacted = _impact(_make_disruption(severity="low"), _make_shipment(route_code="R-01"))
    assert impacted.impact_reason == "both"
    assert impacted.impact_score == 45
    assert "Shipment intersects disruption area and route is directly blocked (+20)" in impacted.factors
    assert not any("(+10)" in factor and "intersects" in factor for factor in impacted.factors)


@pytest.mark.parametrize(
    ("lat", "expected_score", "proximity_factor"),
    [
        (53.5511, 35, "Shipment is within 50 km of disruption (+10)"),
        (54.55, 30, "Shipment is within 150 km of disruption (+5)"),
    ],
)
def test_proximity_contribution(lat, expected_score, proximity_factor):
    impacted = _impact(
        _make_disruption(severity="low", affected_radius_km=200.0),
        _make_shipment(current_lat=lat, current_lng=9.9937),
    )
    assert impacted.impact_score == expected_score
    assert proximity_factor in impacted.factors


def test_temperature_sensitive_cargo_contribution():
    impacted = _impact(shipment=_make_shipment(cargo_type="temperature_sensitive"))
    assert "Temperature-sensitive cargo (+5)" in impacted.factors
    assert impacted.impact_score == 70


def test_hazmat_cargo_contribution():
    impacted = _impact(shipment=_make_shipment(cargo_type="hazmat"))
    assert "Hazmat cargo (+5)" in impacted.factors
    assert impacted.impact_score == 70


def test_duration_over_48_hours_contribution_and_delay_bonus():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    impacted = _impact(
        _make_disruption(start_time=start, estimated_end_time=start + timedelta(hours=72))
    )
    assert "Disruption expected to last more than 48 hours (+5)" in impacted.factors
    assert impacted.impact_score == 70
    assert impacted.estimated_delay_hours == 36.0


def test_duration_over_96_hours_has_additional_contribution():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    impacted = _impact(
        _make_disruption(start_time=start, estimated_end_time=start + timedelta(hours=97))
    )
    assert impacted.impact_score == 75
    assert "Disruption expected to last more than 96 hours (+5)" in impacted.factors


@pytest.mark.parametrize("status", ["at_risk", "delayed"])
def test_existing_risky_or_delayed_status_contribution(status):
    impacted = _impact(shipment=_make_shipment(status=status))
    assert impacted.impact_score == 70
    assert "Shipment is already at risk or delayed (+5)" in impacted.factors


def test_score_is_always_between_zero_and_one_hundred():
    impacted = _impact(_make_disruption(severity="critical"), _make_shipment(route_code="R-01"))
    assert 0 <= impacted.impact_score <= 100


def test_raw_score_over_one_hundred_is_capped_without_changing_factors():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    impacted = _impact(
        _make_disruption(
            severity="critical", start_time=start, estimated_end_time=start + timedelta(hours=97)
        ),
        _make_shipment(route_code="R-01", cargo_type="temperature_sensitive", status="delayed"),
    )
    assert impacted.impact_score == 100
    assert sum(int(factor.rsplit("(+", 1)[1].rstrip(")")) for factor in impacted.factors) == 110
    assert "Disruption expected to last more than 96 hours (+5)" in impacted.factors


def test_estimated_delay_uses_severity_exposure_and_duration_formula():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    impacted = _impact(
        _make_disruption(severity="critical", start_time=start, estimated_end_time=start + timedelta(hours=72)),
        _make_shipment(route_code="R-01"),
    )
    # critical: 48 * both multiplier 1.75 + duration bonus 24
    assert impacted.estimated_delay_hours == 108.0


def test_repeated_execution_is_deterministic():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    disruption = _make_disruption(start_time=start, estimated_end_time=start + timedelta(hours=72))
    shipment = _make_shipment(route_code="R-01", cargo_type="hazmat", status="at_risk")
    assert run(disruption, [shipment]) == run(disruption, [shipment])
