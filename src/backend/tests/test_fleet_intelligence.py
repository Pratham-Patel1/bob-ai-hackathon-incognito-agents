"""
Tests for FleetIntelligenceEngine.
"""
import pytest
import uuid
from backend.engines.fleet_intelligence import analyse_fleet, suggest_redeployments


def _vehicle(**kwargs):
    base = {
        "id": str(uuid.uuid4()),
        "vehicle_id": "TRK-001",
        "type": "truck",
        "status": "active",
        "utilization_pct": 50.0,
        "current_lat": 53.5511,
        "current_lng": 9.9937,
        "capacity_kg": 10000.0,
        "temperature_capable": False,
    }
    base.update(kwargs)
    return base


def _shipment(**kwargs):
    base = {
        "id": str(uuid.uuid4()),
        "tracking_number": "SHP-001",
        "status": "delayed",
        "current_lat": 52.5200,
        "current_lng": 13.4050,  # Berlin
        "weight_kg": 500.0,
        "cargo_type": "general",
        "temperature_required": False,
        "fleet_id": None,
    }
    base.update(kwargs)
    return base


# ── analyse_fleet ─────────────────────────────────────────────────────────────

def test_idle_detection():
    vehicles = [
        _vehicle(id="v1", utilization_pct=10.0),  # idle
        _vehicle(id="v2", utilization_pct=60.0),  # normal
        _vehicle(id="v3", utilization_pct=98.0),  # overloaded
    ]
    analysis = analyse_fleet(vehicles)
    assert analysis.idle_count == 1
    assert "v1" in analysis.idle_vehicle_ids
    assert analysis.overloaded_count == 1
    assert "v3" in analysis.overloaded_vehicle_ids


def test_offline_vehicle_not_counted_as_idle():
    vehicles = [_vehicle(id="v1", utilization_pct=5.0, status="offline")]
    analysis = analyse_fleet(vehicles)
    assert analysis.idle_count == 0


def test_histogram_populated():
    vehicles = [
        _vehicle(utilization_pct=10.0),
        _vehicle(utilization_pct=40.0),
        _vehicle(utilization_pct=70.0),
        _vehicle(utilization_pct=90.0),
        _vehicle(utilization_pct=99.0),
    ]
    analysis = analyse_fleet(vehicles)
    assert analysis.utilization_histogram["0-20"] == 1
    assert analysis.utilization_histogram["20-50"] == 1
    assert analysis.utilization_histogram["50-80"] == 1
    assert analysis.utilization_histogram["80-95"] == 1
    assert analysis.utilization_histogram["95-100"] == 1


def test_empty_fleet():
    analysis = analyse_fleet([])
    assert analysis.idle_count == 0
    assert analysis.overloaded_count == 0


# ── suggest_redeployments ─────────────────────────────────────────────────────

def test_nearest_match():
    idle_vehicle = _vehicle(
        id="v1",
        status="active",
        utilization_pct=5.0,
        current_lat=53.5511,   # Hamburg
        current_lng=9.9937,
        capacity_kg=10000.0,
    )
    near_shipment = _shipment(
        id="s1",
        current_lat=52.5200,   # Berlin ~260 km
        current_lng=13.4050,
        weight_kg=500.0,
    )
    far_shipment = _shipment(
        id="s2",
        current_lat=48.8566,   # Paris ~900 km
        current_lng=2.3522,
        weight_kg=500.0,
    )
    suggestions = suggest_redeployments([idle_vehicle], [near_shipment, far_shipment])
    assert len(suggestions) == 1
    assert suggestions[0].target_shipment_id == "s1"  # nearest


def test_capacity_constraint():
    idle_vehicle = _vehicle(
        id="v1", status="active", utilization_pct=5.0,
        current_lat=53.5511, current_lng=9.9937, capacity_kg=100.0,
    )
    heavy_shipment = _shipment(
        id="s1", current_lat=52.5200, current_lng=13.4050, weight_kg=500.0,
    )
    suggestions = suggest_redeployments([idle_vehicle], [heavy_shipment])
    assert len(suggestions) == 0  # too heavy


def test_temperature_constraint():
    idle_vehicle = _vehicle(
        id="v1", status="active", utilization_pct=5.0,
        current_lat=53.5511, current_lng=9.9937,
        temperature_capable=False, capacity_kg=10000.0,
    )
    cold_shipment = _shipment(
        id="s1", current_lat=52.5200, current_lng=13.4050,
        temperature_required=True,
    )
    suggestions = suggest_redeployments([idle_vehicle], [cold_shipment])
    assert len(suggestions) == 0  # vehicle not temp-capable


def test_no_idle_vehicles():
    busy = _vehicle(id="v1", utilization_pct=80.0)
    shipment = _shipment()
    suggestions = suggest_redeployments([busy], [shipment])
    assert len(suggestions) == 0
