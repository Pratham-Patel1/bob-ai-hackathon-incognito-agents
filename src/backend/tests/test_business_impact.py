"""
Tests for BusinessImpactEngine.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import pytest

from backend.engines.business_impact import (
    BusinessImpact,
    ShipmentImpact,
    run,
)


def _dt_str(hours_from_base: float, base: datetime | None = None) -> str:
    if base is None:
        base = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
    dt = base + timedelta(hours=hours_from_base)
    return dt.isoformat()


def _shipment(
    shipment_id: str = "shp-1",
    tracking_number: str = "TRK-001",
    cargo_value_usd: float = 50_000.0,
    scheduled_arrival: Any = "2026-09-14T12:00:00Z",
    estimated_arrival: Any = "2026-09-14T16:00:00Z",
    **kwargs: Any,
) -> dict[str, Any]:
    base = {
        "id": shipment_id,
        "tracking_number": tracking_number,
        "cargo_value_usd": cargo_value_usd,
        "scheduled_arrival": scheduled_arrival,
        "estimated_arrival": estimated_arrival,
    }
    base.update(kwargs)
    return base


def test_empty_shipment_list():
    """1. Empty shipment list returns zeroed summary and valid explanation."""
    result = run([])

    assert isinstance(result, BusinessImpact)
    assert result.total_cargo_value_at_risk_usd == 0.0
    assert result.total_delay_hours == 0.0
    assert result.avg_delay_hours == 0.0
    assert result.cost_of_delay_usd == 0.0
    assert result.penalty_exposure_usd == 0.0
    assert result.sla_breach_count == 0
    assert result.shipment_breakdown == []
    assert "0 shipments affected" in result.explanation


def test_shipment_with_zero_delay():
    """2. Shipment arriving on time or early has zero delay and zero penalties."""
    # Exactly on time
    s_ontime = _shipment(
        scheduled_arrival="2026-09-14T12:00:00Z",
        estimated_arrival="2026-09-14T12:00:00Z",
    )
    result_ontime = run([s_ontime])
    assert result_ontime.total_delay_hours == 0.0
    assert result_ontime.cost_of_delay_usd == 0.0
    assert result_ontime.sla_breach_count == 0
    assert result_ontime.penalty_exposure_usd == 0.0

    # Arriving early
    s_early = _shipment(
        scheduled_arrival="2026-09-14T12:00:00Z",
        estimated_arrival="2026-09-14T10:00:00Z",
    )
    result_early = run([s_early])
    assert result_early.total_delay_hours == 0.0
    assert result_early.cost_of_delay_usd == 0.0
    assert result_early.sla_breach_count == 0


def test_exactly_4_hours_delay_is_not_sla_breach():
    """3. Exactly 4 hours delay (equal to sla_buffer_hours) should NOT be an SLA breach."""
    s = _shipment(
        scheduled_arrival="2026-09-14T12:00:00Z",
        estimated_arrival="2026-09-14T16:00:00Z",  # exactly +4 hours
    )

    result = run([s], sla_buffer_hours=4.0, sla_penalty_usd=5000.0)

    assert result.total_delay_hours == 4.0
    assert result.sla_breach_count == 0
    assert result.penalty_exposure_usd == 0.0
    assert result.shipment_breakdown[0].sla_breach is False
    assert result.shipment_breakdown[0].penalty_exposure_usd == 0.0


def test_more_than_4_hours_delay_is_sla_breach():
    """4. More than 4 hours delay (> sla_buffer_hours) should trigger an SLA breach."""
    s = _shipment(
        scheduled_arrival="2026-09-14T12:00:00Z",
        estimated_arrival="2026-09-14T17:00:00Z",  # +5 hours
    )

    result = run([s], sla_buffer_hours=4.0, sla_penalty_usd=5000.0)

    assert result.total_delay_hours == 5.0
    assert result.sla_breach_count == 1
    assert result.penalty_exposure_usd == 5000.0
    assert result.shipment_breakdown[0].sla_breach is True
    assert result.shipment_breakdown[0].penalty_exposure_usd == 5000.0


def test_multiple_shipments_aggregation():
    """5. Multiple shipments are correctly aggregated for value, delay, average delay, cost, and penalties."""
    s1 = _shipment(
        shipment_id="shp-1",
        cargo_value_usd=100_000.0,
        scheduled_arrival="2026-09-14T12:00:00Z",
        estimated_arrival="2026-09-14T16:00:00Z",  # 4h delay, no breach
    )
    s2 = _shipment(
        shipment_id="shp-2",
        cargo_value_usd=200_000.0,
        scheduled_arrival="2026-09-14T12:00:00Z",
        estimated_arrival="2026-09-14T20:00:00Z",  # 8h delay, SLA breach
    )

    result = run([s1, s2], daily_holding_cost_rate=0.002, sla_buffer_hours=4.0, sla_penalty_usd=5000.0)

    assert len(result.shipment_breakdown) == 2
    assert result.total_cargo_value_at_risk_usd == 300_000.0
    assert result.total_delay_hours == 12.0
    assert result.avg_delay_hours == 6.0
    assert result.sla_breach_count == 1
    assert result.penalty_exposure_usd == 5000.0

    # s1 cost: (4 / 24) * 100,000 * 0.002 = 33.33
    # s2 cost: (8 / 24) * 200,000 * 0.002 = 133.33
    # total cost = 166.67
    assert result.cost_of_delay_usd == pytest.approx(166.67, abs=0.01)


def test_cargo_value_affects_cost_of_delay():
    """6. Higher cargo value proportionally increases cost of delay for identical delay duration."""
    # 24 hours delay = 1 full day -> cost is cargo_value * daily_holding_cost_rate
    s_small = _shipment(
        cargo_value_usd=10_000.0,
        scheduled_arrival="2026-09-14T00:00:00Z",
        estimated_arrival="2026-09-15T00:00:00Z",
    )
    s_large = _shipment(
        cargo_value_usd=100_000.0,
        scheduled_arrival="2026-09-14T00:00:00Z",
        estimated_arrival="2026-09-15T00:00:00Z",
    )

    res_small = run([s_small], daily_holding_cost_rate=0.002)
    res_large = run([s_large], daily_holding_cost_rate=0.002)

    assert res_small.cost_of_delay_usd == pytest.approx(20.0, abs=0.01)
    assert res_large.cost_of_delay_usd == pytest.approx(200.0, abs=0.01)
    assert res_large.cost_of_delay_usd == pytest.approx(res_small.cost_of_delay_usd * 10, abs=0.01)


def test_missing_scheduled_arrival_does_not_crash():
    """7. Missing or None scheduled_arrival does not crash and defaults delay to 0.0."""
    s1 = _shipment(scheduled_arrival=None, estimated_arrival="2026-09-14T18:00:00Z")
    s2 = {"id": "shp-no-sched", "cargo_value_usd": 15000.0, "estimated_arrival": "2026-09-14T18:00:00Z"}

    result = run([s1, s2])

    assert isinstance(result, BusinessImpact)
    assert result.total_delay_hours == 0.0
    assert result.cost_of_delay_usd == 0.0
    assert result.sla_breach_count == 0


def test_missing_estimated_arrival_does_not_crash():
    """8. Missing or None estimated_arrival does not crash and defaults delay to 0.0."""
    s1 = _shipment(scheduled_arrival="2026-09-14T12:00:00Z", estimated_arrival=None)
    s2 = {"id": "shp-no-est", "cargo_value_usd": 25000.0, "scheduled_arrival": "2026-09-14T12:00:00Z"}

    result = run([s1, s2])

    assert isinstance(result, BusinessImpact)
    assert result.total_delay_hours == 0.0
    assert result.cost_of_delay_usd == 0.0
    assert result.sla_breach_count == 0


def test_iso_datetime_strings_parsed_correctly():
    """9. ISO datetime strings in various formats (UTC 'Z', offset '+00:00', naive ISO string) are parsed correctly."""
    s_z = _shipment(
        scheduled_arrival="2026-09-14T10:00:00Z",
        estimated_arrival="2026-09-14T16:00:00Z",
    )
    s_offset = _shipment(
        scheduled_arrival="2026-09-14T10:00:00+00:00",
        estimated_arrival="2026-09-14T16:00:00+00:00",
    )
    s_no_tz = _shipment(
        scheduled_arrival="2026-09-14T10:00:00",
        estimated_arrival="2026-09-14T16:00:00",
    )

    for s in [s_z, s_offset, s_no_tz]:
        res = run([s])
        assert res.total_delay_hours == 6.0


def test_naive_datetime_handled_correctly():
    """10. Native datetime objects without tzinfo are handled and converted to UTC properly."""
    dt_sched = datetime(2026, 9, 14, 10, 0, 0)
    dt_est = datetime(2026, 9, 14, 18, 30, 0)

    s = _shipment(scheduled_arrival=dt_sched, estimated_arrival=dt_est)
    result = run([s])

    assert result.total_delay_hours == 8.5
    assert result.shipment_breakdown[0].delay_hours == 8.5


def test_explanation_contains_required_metrics():
    """11. Explanation contains affected shipment count, cost of delay, SLA breach count, and average delay."""
    s1 = _shipment(
        shipment_id="s1",
        cargo_value_usd=50_000.0,
        scheduled_arrival="2026-09-14T10:00:00Z",
        estimated_arrival="2026-09-14T16:00:00Z",  # 6h delay -> SLA breach
    )
    s2 = _shipment(
        shipment_id="s2",
        cargo_value_usd=50_000.0,
        scheduled_arrival="2026-09-14T10:00:00Z",
        estimated_arrival="2026-09-14T12:00:00Z",  # 2h delay -> no breach
    )

    result = run([s1, s2])

    exp = result.explanation
    # Check affected shipment count
    assert "2 shipments affected" in exp
    # Check cost of delay
    assert "Estimated cost of delay:" in exp
    # Check SLA breach count
    assert "SLA breaches: 1" in exp
    # Check average delay (4.0h)
    assert "Avg delay: 4.0h" in exp


def test_verify_shipment_breakdown_fields():
    """12. Verify all ShipmentImpact dataclass fields are properly populated."""
    s = _shipment(
        shipment_id="shp-xyz",
        tracking_number="TRK-9999",
        cargo_value_usd=80_000.0,
        scheduled_arrival="2026-09-14T08:00:00Z",
        estimated_arrival="2026-09-14T20:00:00Z",  # 12h delay
    )

    result = run([s], daily_holding_cost_rate=0.002, sla_buffer_hours=4.0, sla_penalty_usd=5000.0)

    assert len(result.shipment_breakdown) == 1
    impact = result.shipment_breakdown[0]

    assert isinstance(impact, ShipmentImpact)
    assert impact.shipment_id == "shp-xyz"
    assert impact.tracking_number == "TRK-9999"
    assert impact.cargo_value_usd == 80_000.0
    assert impact.delay_hours == 12.0
    # Cost: (12 / 24) * 80_000 * 0.002 = 80.0
    assert impact.cost_of_delay_usd == 80.0
    assert impact.sla_breach is True
    assert impact.penalty_exposure_usd == 5000.0
