"""
Tests for FleetIntelligenceEngine — Phase 2C

Run with:
    pytest src/backend/tests/test_fleet_intelligence.py -v
"""

from __future__ import annotations

import pytest

from backend.engines.fleet_intelligence import (
    FleetIntelligenceResult,
    FleetVehicleSummary,
    IDLE_UTILISATION_THRESHOLD,
    OVERLOADED_UTILISATION_THRESHOLD,
    _haversine_km,
    _suitability_score,
    analyse_fleet,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vehicle(
    id: str = "V001",
    vehicle_code: str = "TRK-001",
    vehicle_type: str = "truck",
    capacity_tons: float = 20.0,
    current_load_tons: float = 5.0,
    is_refrigerated: bool = False,
    status: str = "available",
    latitude: float = 19.0760,
    longitude: float = 72.8777,
) -> dict:
    return {
        "id": id,
        "vehicle_code": vehicle_code,
        "vehicle_type": vehicle_type,
        "capacity_tons": capacity_tons,
        "current_load_tons": current_load_tons,
        "is_refrigerated": is_refrigerated,
        "status": status,
        "latitude": latitude,
        "longitude": longitude,
    }


def _make_fleet(specs: list[dict]) -> list[dict]:
    return [_vehicle(**s) for s in specs]


# ---------------------------------------------------------------------------
# Haversine helper
# ---------------------------------------------------------------------------

class TestHaversine:
    def test_same_point_is_zero(self):
        assert _haversine_km(19.0, 72.0, 19.0, 72.0) == pytest.approx(0.0, abs=0.01)

    def test_known_distance(self):
        # Mumbai to Pune ≈ 120 km straight line
        dist = _haversine_km(19.0760, 72.8777, 18.5204, 73.8567)
        assert 110 < dist < 135

    def test_returns_float(self):
        assert isinstance(_haversine_km(0, 0, 1, 1), float)


# ---------------------------------------------------------------------------
# Utilisation thresholds
# ---------------------------------------------------------------------------

class TestUtilisationClassification:
    def test_idle_vehicle_classified_correctly(self):
        """Vehicle with < 20% utilisation should be in idle list"""
        fleet = [_vehicle(capacity_tons=20.0, current_load_tons=1.0, status="available")]  # 5%
        result = analyse_fleet(fleet)
        assert len(result.idle_vehicles) == 1

    def test_available_non_idle_classified_correctly(self):
        """Vehicle with 50% utilisation should be in available, not idle"""
        fleet = [_vehicle(capacity_tons=20.0, current_load_tons=10.0, status="available")]  # 50%
        result = analyse_fleet(fleet)
        assert len(result.idle_vehicles) == 0
        assert len(result.available_vehicles) == 1

    def test_overloaded_vehicle_classified_correctly(self):
        """Vehicle with > 95% utilisation should be in overloaded list"""
        fleet = [_vehicle(capacity_tons=20.0, current_load_tons=19.5, status="in_transit")]  # 97.5%
        result = analyse_fleet(fleet)
        assert len(result.overloaded_vehicles) == 1

    def test_in_transit_counted_correctly(self):
        fleet = [_vehicle(status="in_transit")]
        result = analyse_fleet(fleet)
        assert result.summary.in_transit_count == 1

    def test_maintenance_counted_correctly(self):
        fleet = [_vehicle(status="maintenance")]
        result = analyse_fleet(fleet)
        assert result.summary.maintenance_count == 1


# ---------------------------------------------------------------------------
# Empty fleet
# ---------------------------------------------------------------------------

class TestEmptyFleet:
    def test_empty_fleet_returns_result(self):
        result = analyse_fleet([])
        assert isinstance(result, FleetIntelligenceResult)
        assert result.summary.total_vehicles == 0
        assert result.redeployment_candidates == []


# ---------------------------------------------------------------------------
# Reefer matching
# ---------------------------------------------------------------------------

class TestReeferMatching:
    def test_refrigerated_available_counted(self):
        fleet = [
            _vehicle(is_refrigerated=True, status="available"),
            _vehicle(id="V2", vehicle_code="TRK-002", is_refrigerated=False, status="available"),
        ]
        result = analyse_fleet(fleet)
        assert result.summary.refrigerated_available == 1

    def test_reefer_prioritised_in_candidates_when_required(self):
        fleet = [
            _vehicle(id="V1", vehicle_code="TRK-001", is_refrigerated=True,
                     status="available", latitude=19.0, longitude=72.0),
            _vehicle(id="V2", vehicle_code="TRK-002", is_refrigerated=False,
                     status="available", latitude=19.0, longitude=72.0),
        ]
        ctx = {"requires_reefer": True, "required_capacity": 5.0}
        result = analyse_fleet(fleet, request_context=ctx)
        assert result.redeployment_candidates[0].is_refrigerated is True


# ---------------------------------------------------------------------------
# Proximity sorting
# ---------------------------------------------------------------------------

class TestProximitySorting:
    def test_closer_vehicle_ranked_higher(self):
        """Vehicle near epicenter should rank above far vehicle."""
        # Epicenter in Mumbai
        epicenter = {"epicenter_lat": 19.0760, "epicenter_lng": 72.8777}
        fleet = [
            # Near Mumbai
            _vehicle(id="V1", vehicle_code="NEAR", latitude=19.1, longitude=72.9,
                     current_load_tons=0.0, status="available"),
            # Far (Delhi)
            _vehicle(id="V2", vehicle_code="FAR", latitude=28.6139, longitude=77.2090,
                     current_load_tons=0.0, status="available"),
        ]
        result = analyse_fleet(fleet, request_context=epicenter)
        codes = [v.vehicle_code for v in result.redeployment_candidates]
        assert codes[0] == "NEAR"


# ---------------------------------------------------------------------------
# Capacity matching
# ---------------------------------------------------------------------------

class TestCapacityMatching:
    def test_capacity_below_required_lowers_score(self):
        v_ample = FleetVehicleSummary(
            id="V1", vehicle_code="A", vehicle_type="truck",
            capacity_tons=20.0, current_load_tons=0.0, utilisation_percent=0.0,
            is_refrigerated=False, status="available",
            latitude=0.0, longitude=0.0, distance_km=100.0, suitability_score=0.0,
        )
        v_small = FleetVehicleSummary(
            id="V2", vehicle_code="B", vehicle_type="truck",
            capacity_tons=3.0, current_load_tons=0.0, utilisation_percent=0.0,
            is_refrigerated=False, status="available",
            latitude=0.0, longitude=0.0, distance_km=100.0, suitability_score=0.0,
        )
        score_ample = _suitability_score(v_ample, 10.0, False, 500.0)
        score_small = _suitability_score(v_small, 10.0, False, 500.0)
        assert score_ample > score_small


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

class TestSummaryStats:
    def test_total_vehicles_correct(self):
        fleet = [_vehicle(), _vehicle(id="V2", vehicle_code="TRK-002")]
        result = analyse_fleet(fleet)
        assert result.summary.total_vehicles == 2

    def test_average_utilisation_correct(self):
        fleet = [
            _vehicle(capacity_tons=10.0, current_load_tons=0.0),   # 0%
            _vehicle(id="V2", vehicle_code="TRK-002",
                     capacity_tons=10.0, current_load_tons=10.0),  # 100%
        ]
        result = analyse_fleet(fleet)
        assert result.summary.average_utilisation_percent == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_returns_fleet_intelligence_result(self):
        result = analyse_fleet([_vehicle()])
        assert isinstance(result, FleetIntelligenceResult)

    def test_factors_list_of_strings(self):
        result = analyse_fleet([_vehicle()])
        assert isinstance(result.factors, list)
        assert all(isinstance(f, str) for f in result.factors)

    def test_distance_populated_when_epicenter_given(self):
        fleet = [_vehicle(latitude=19.0, longitude=72.0, status="available")]
        ctx = {"epicenter_lat": 19.1, "epicenter_lng": 72.1}
        result = analyse_fleet(fleet, request_context=ctx)
        cand = result.redeployment_candidates[0]
        assert cand.distance_km is not None
        assert cand.distance_km > 0

    def test_no_distance_when_no_epicenter(self):
        fleet = [_vehicle(status="available")]
        result = analyse_fleet(fleet)
        assert result.redeployment_candidates[0].distance_km is None
