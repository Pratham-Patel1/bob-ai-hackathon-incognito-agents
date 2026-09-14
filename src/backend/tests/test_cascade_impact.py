"""
Tests for BusinessImpactEngine and CascadingImpactEngine.
"""
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from backend.engines.business_impact import run as biz_run
from backend.engines.cascade_impact import run as cascade_run


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat()


# ── BusinessImpactEngine ──────────────────────────────────────────────────────

def test_no_delay_no_cost():
    arrival = _now() + timedelta(hours=24)
    shipments = [{
        "id": "s1",
        "tracking_number": "SHP-001",
        "cargo_value_usd": 100_000,
        "scheduled_arrival": _iso(arrival),
        "estimated_arrival": _iso(arrival),  # no delay
    }]
    result = biz_run(shipments)
    assert result.total_delay_hours == 0.0
    assert result.cost_of_delay_usd == 0.0
    assert result.sla_breach_count == 0


def test_delay_generates_cost():
    scheduled = _now() + timedelta(hours=24)
    estimated = scheduled + timedelta(hours=12)  # 12h delay
    shipments = [{
        "id": "s1",
        "tracking_number": "SHP-001",
        "cargo_value_usd": 100_000,
        "scheduled_arrival": _iso(scheduled),
        "estimated_arrival": _iso(estimated),
    }]
    result = biz_run(shipments, daily_holding_cost_rate=0.002)
    assert result.total_delay_hours == pytest.approx(12.0, abs=0.1)
    expected_cost = (12 / 24) * 100_000 * 0.002
    assert result.cost_of_delay_usd == pytest.approx(expected_cost, abs=0.1)


def test_sla_breach():
    scheduled = _now() + timedelta(hours=24)
    estimated = scheduled + timedelta(hours=8)  # 8h > 4h SLA buffer
    shipments = [{
        "id": "s1",
        "tracking_number": "SHP-001",
        "cargo_value_usd": 50_000,
        "scheduled_arrival": _iso(scheduled),
        "estimated_arrival": _iso(estimated),
    }]
    result = biz_run(shipments, sla_buffer_hours=4.0, sla_penalty_usd=5_000.0)
    assert result.sla_breach_count == 1
    assert result.penalty_exposure_usd == 5_000.0


def test_multiple_shipments_aggregated():
    s = _now() + timedelta(hours=48)
    e = s + timedelta(hours=6)
    shipments = [
        {"id": "s1", "tracking_number": "A", "cargo_value_usd": 50_000,
         "scheduled_arrival": _iso(s), "estimated_arrival": _iso(e)},
        {"id": "s2", "tracking_number": "B", "cargo_value_usd": 30_000,
         "scheduled_arrival": _iso(s), "estimated_arrival": _iso(e)},
    ]
    result = biz_run(shipments)
    assert result.total_delay_hours == pytest.approx(12.0, abs=0.1)
    assert result.total_cargo_value_at_risk_usd == pytest.approx(80_000.0)


def test_empty_shipments():
    result = biz_run([])
    assert result.total_delay_hours == 0.0
    assert result.sla_breach_count == 0


# ── CascadingImpactEngine ─────────────────────────────────────────────────────

def _ship(sid, status="in_transit", fleet_id=None, carrier_id=None, value=10_000):
    return {
        "id": sid,
        "tracking_number": f"SHP-{sid}",
        "status": status,
        "fleet_id": fleet_id,
        "carrier_id": carrier_id,
        "cargo_value_usd": value,
        "scheduled_departure": _iso(_now()),
    }


def test_fleet_cascade():
    fid = "fleet-1"
    direct = _ship("direct-1", status="in_transit", fleet_id=fid)
    secondary = _ship("sec-1", status="in_transit", fleet_id=fid)
    unrelated = _ship("unrel-1", status="in_transit", fleet_id="fleet-2")

    result = cascade_run(
        direct_shipment_ids={"direct-1"},
        all_shipments=[direct, secondary, unrelated],
        fleet=[],
    )
    assert result.secondary_count == 1
    sec_ids = [n.shipment_id for n in result.cascade_chain]
    assert "sec-1" in sec_ids
    assert "unrel-1" not in sec_ids


def test_carrier_cascade_threshold():
    cid = "carrier-1"
    # 4 shipments on this carrier; 2 are direct (50% > 30% threshold)
    shipments = [
        _ship(f"d{i}", status="in_transit", carrier_id=cid) for i in range(2)  # direct
    ] + [
        _ship(f"s{i}", status="in_transit", carrier_id=cid) for i in range(2)  # secondary
    ]
    direct_ids = {"d0", "d1"}

    result = cascade_run(
        direct_shipment_ids=direct_ids,
        all_shipments=shipments,
        fleet=[],
    )
    assert result.secondary_count == 2
    assert all(n.impact_type == "carrier_cascade" for n in result.cascade_chain)


def test_no_secondary_when_below_threshold():
    cid = "carrier-1"
    # 10 shipments on carrier; only 1 direct (10% < 30% threshold)
    shipments = [_ship(f"x{i}", status="in_transit", carrier_id=cid) for i in range(10)]
    direct_ids = {"x0"}
    result = cascade_run(
        direct_shipment_ids=direct_ids,
        all_shipments=shipments,
        fleet=[],
    )
    assert result.secondary_count == 0


def test_direct_count_correct():
    shipments = [_ship(f"d{i}", status="in_transit") for i in range(3)]
    result = cascade_run(
        direct_shipment_ids={"d0", "d1", "d2"},
        all_shipments=shipments,
        fleet=[],
    )
    assert result.direct_count == 3
