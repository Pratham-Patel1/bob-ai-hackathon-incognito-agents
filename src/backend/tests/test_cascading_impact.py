"""
Tests for CascadingImpactEngine — Phase 2E

Run with:
    pytest src/backend/tests/test_cascading_impact.py -v
"""

from __future__ import annotations

import pytest

from backend.engines.cascading_impact import (
    CASCADE_DEPTH,
    SAME_HUB_RADIUS_KM,
    CascadeImpactResult,
    CascadeShipmentImpact,
    CascadeVehicleConflict,
    compute_cascade_impact,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _shipment(
    id: str = "S001",
    tracking_number: str = "TRK001",
    route_id: str = "R001",
    fleet_id: str = "V001",
    carrier_id: str = "C001",
    status: str = "in_transit",
    current_lat: float = 19.076,
    current_lng: float = 72.877,
) -> dict:
    return {
        "id": id,
        "tracking_number": tracking_number,
        "route_id": route_id,
        "fleet_id": fleet_id,
        "carrier_id": carrier_id,
        "status": status,
        "current_lat": current_lat,
        "current_lng": current_lng,
        "origin_lat": current_lat,
        "origin_lng": current_lng,
    }


def _vehicle(
    id: str = "V001",
    vehicle_code: str = "TRK-001",
    status: str = "in_transit",
    latitude: float = 19.076,
    longitude: float = 72.877,
) -> dict:
    return {
        "id": id,
        "vehicle_code": vehicle_code,
        "status": status,
        "latitude": latitude,
        "longitude": longitude,
    }


def _disruption(
    severity: str = "medium",
    latitude: float = 19.076,
    longitude: float = 72.877,
    radius_km: float = 50.0,
) -> dict:
    return {
        "id": "D001",
        "severity": severity,
        "latitude": latitude,
        "longitude": longitude,
        "radius_km": radius_km,
    }


# ---------------------------------------------------------------------------
# Empty inputs
# ---------------------------------------------------------------------------

class TestEmptyInputs:
    def test_no_other_shipments_no_cascade(self):
        result = compute_cascade_impact(_shipment(), [], [])
        assert isinstance(result, CascadeImpactResult)
        assert result.potentially_delayed_shipments == []
        assert result.vehicle_conflicts == []

    def test_depth_is_always_one(self):
        result = compute_cascade_impact(_shipment(), [], [])
        assert result.cascade_depth == CASCADE_DEPTH == 1

    def test_primary_always_in_directly_affected(self):
        result = compute_cascade_impact(_shipment(id="PRIMARY"), [], [])
        assert "PRIMARY" in result.directly_affected_shipment_ids


# ---------------------------------------------------------------------------
# Delivered / cancelled shipments excluded
# ---------------------------------------------------------------------------

class TestExcludeTerminalStatus:
    def test_delivered_shipment_not_cascaded(self):
        primary = _shipment(id="S1", route_id="R1")
        other   = _shipment(id="S2", tracking_number="TRK002",
                            route_id="R1", status="delivered")
        result = compute_cascade_impact(primary, [other], [])
        assert len(result.potentially_delayed_shipments) == 0


# ---------------------------------------------------------------------------
# Route-based cascade
# ---------------------------------------------------------------------------

class TestRouteCascade:
    def test_same_route_causes_cascade(self):
        primary = _shipment(id="S1", route_id="ROUTE_X")
        other   = _shipment(id="S2", tracking_number="TRK002", route_id="ROUTE_X")
        result  = compute_cascade_impact(primary, [other], [])
        assert len(result.potentially_delayed_shipments) == 1
        assert result.potentially_delayed_shipments[0].shipment_id == "S2"
        assert "route" in result.potentially_delayed_shipments[0].reason.lower()

    def test_different_route_no_cascade(self):
        primary = _shipment(id="S1", route_id="ROUTE_A",
                            fleet_id="V_PRIMARY", carrier_id="C_PRIMARY")
        other   = _shipment(id="S2", tracking_number="TRK002",
                            route_id="ROUTE_B",
                            fleet_id="V_OTHER",   carrier_id="C_OTHER",
                            current_lat=40.0, current_lng=100.0)   # far away
        result = compute_cascade_impact(primary, [other], [])
        assert len(result.potentially_delayed_shipments) == 0


# ---------------------------------------------------------------------------
# Fleet-based cascade
# ---------------------------------------------------------------------------

class TestFleetCascade:
    def test_same_vehicle_causes_cascade(self):
        primary = _shipment(id="S1", fleet_id="VEH_X")
        other   = _shipment(id="S2", tracking_number="TRK002", fleet_id="VEH_X",
                            route_id="OTHER_ROUTE")
        result = compute_cascade_impact(primary, [other], [])
        assert any(c.shipment_id == "S2" for c in result.potentially_delayed_shipments)


# ---------------------------------------------------------------------------
# Geographic cascade
# ---------------------------------------------------------------------------

class TestGeoCascade:
    def test_nearby_shipment_cascades(self):
        primary = _shipment(id="S1", current_lat=19.076, current_lng=72.877,
                            route_id="R1", fleet_id="V1", carrier_id="C1")
        # 1km away — well within 50km hub radius
        other   = _shipment(id="S2", tracking_number="TRK002",
                            current_lat=19.085, current_lng=72.877,
                            route_id="R2", fleet_id="V2", carrier_id="C2")
        result = compute_cascade_impact(primary, [other], [])
        assert len(result.potentially_delayed_shipments) == 1

    def test_far_shipment_no_cascade(self):
        primary = _shipment(id="S1", current_lat=19.076, current_lng=72.877,
                            route_id="R1", fleet_id="V1", carrier_id="C1")
        # Delhi — ~1400km away
        other   = _shipment(id="S2", tracking_number="TRK002",
                            current_lat=28.613, current_lng=77.209,
                            route_id="R2", fleet_id="V2", carrier_id="C2")
        result = compute_cascade_impact(primary, [other], [])
        assert len(result.potentially_delayed_shipments) == 0


# ---------------------------------------------------------------------------
# Vehicle conflicts
# ---------------------------------------------------------------------------

class TestVehicleConflicts:
    def test_assigned_vehicle_flagged_for_reassignment(self):
        primary = _shipment(id="S1", fleet_id="VEH_ASSIGNED")
        vehicle = _vehicle(id="VEH_ASSIGNED", vehicle_code="TRK-ASSIGNED")
        result  = compute_cascade_impact(primary, [], [vehicle])
        assert len(result.vehicle_conflicts) == 1
        assert result.vehicle_conflicts[0].impact == "reassignment_needed"

    def test_nearby_vehicle_flagged_at_risk(self):
        primary = _shipment(id="S1", fleet_id="VEH_OTHER",
                            current_lat=19.076, current_lng=72.877)
        # Vehicle within 100km but not the assigned one
        vehicle = _vehicle(id="VEH_NEAR", vehicle_code="TRK-NEAR",
                           latitude=19.3, longitude=72.9)
        disruption = _disruption(latitude=19.076, longitude=72.877, radius_km=50.0)
        result = compute_cascade_impact(primary, [], [vehicle], disruption)
        # Vehicle is nearby — should be in conflicts
        assert any(v.vehicle_id == "VEH_NEAR" for v in result.vehicle_conflicts)

    def test_maintenance_vehicle_excluded(self):
        primary = _shipment(id="S1", fleet_id="NONE",
                            current_lat=19.076, current_lng=72.877)
        vehicle = _vehicle(id="V_MAINT", status="maintenance",
                           latitude=19.076, longitude=72.877)
        result = compute_cascade_impact(primary, [], [vehicle])
        assert not any(v.vehicle_id == "V_MAINT" for v in result.vehicle_conflicts)


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_returns_cascade_impact_result(self):
        result = compute_cascade_impact(_shipment(), [], [])
        assert isinstance(result, CascadeImpactResult)

    def test_total_affected_count_correct(self):
        primary = _shipment(id="S1", route_id="ROUTE_X", fleet_id="VEH_1")
        other   = _shipment(id="S2", tracking_number="TRK2", route_id="ROUTE_X")
        vehicle = _vehicle(id="VEH_1")
        result  = compute_cascade_impact(primary, [other], [vehicle])
        assert result.total_affected_count == len(result.potentially_delayed_shipments) + len(result.vehicle_conflicts)

    def test_factors_list_of_strings(self):
        result = compute_cascade_impact(_shipment(), [], [])
        assert all(isinstance(f, str) for f in result.factors)

    def test_primary_not_in_downstream_shipments(self):
        primary = _shipment(id="PRIMARY", route_id="ROUTE_X")
        # No other shipments passed
        result = compute_cascade_impact(primary, [], [])
        ids = [c.shipment_id for c in result.potentially_delayed_shipments]
        assert "PRIMARY" not in ids

    def test_delay_estimate_matches_severity(self):
        primary = _shipment(id="S1", route_id="RX", fleet_id="VX", carrier_id="CX")
        other   = _shipment(id="S2", tracking_number="T2", route_id="RX")
        disruption_crit = _disruption(severity="critical")
        disruption_low  = _disruption(severity="low")
        r_crit = compute_cascade_impact(primary, [other], [], disruption_crit)
        r_low  = compute_cascade_impact(primary, [other], [], disruption_low)
        assert (r_crit.potentially_delayed_shipments[0].estimated_extra_delay_hours >
                r_low.potentially_delayed_shipments[0].estimated_extra_delay_hours)
