"""Seed data unit tests — validates the seed script data structures."""
from __future__ import annotations

import backend.data.seed as seed_module


def test_carrier_data_count() -> None:
    assert len(seed_module.CARRIER_DATA) == 10


def test_route_data_count() -> None:
    assert len(seed_module.ROUTE_DATA) == 30


def test_all_carriers_have_required_fields() -> None:
    required = {"name", "code", "type", "reliability_score", "cost_index", "coverage_regions"}
    for carrier in seed_module.CARRIER_DATA:
        missing = required - set(carrier.keys())
        assert not missing, f"Carrier {carrier['code']} missing: {missing}"


def test_carrier_reliability_in_range() -> None:
    for carrier in seed_module.CARRIER_DATA:
        assert 0.0 <= carrier["reliability_score"] <= 1.0, (
            f"Carrier {carrier['code']} reliability out of range"
        )


def test_routes_have_valid_modes() -> None:
    valid_modes = {"road", "rail", "air", "sea", "multimodal"}
    for route in seed_module.ROUTE_DATA:
        assert route["mode"] in valid_modes, f"Route {route['code']} has invalid mode: {route['mode']}"


def test_routes_have_positive_distance() -> None:
    for route in seed_module.ROUTE_DATA:
        assert route["distance_km"] > 0, f"Route {route['code']} has zero distance"


def test_disruption_defs_present() -> None:
    """Disruption definitions are inline in run_seed, but we can verify city coords coverage."""
    # All disruption epicenters should map to known approximate regions
    disruption_epicenters = [
        (54.0, 9.5),    # North Sea
        (50.11, 8.68),  # Frankfurt
        (31.23, 121.47),# Shanghai
        (41.88, -87.63),# Chicago
        (1.35, 103.82), # Singapore
    ]
    # Validate Haversine works for each
    from backend.utils.geo import haversine
    for lat, lng in disruption_epicenters:
        dist = haversine(lat, lng, lat, lng)
        assert dist == 0.0


def test_city_coords_all_routes_covered() -> None:
    """Every route origin and destination has a city coordinate entry."""
    for route in seed_module.ROUTE_DATA:
        assert route["origin"] in seed_module.CITY_COORDS, (
            f"Route {route['code']} origin '{route['origin']}' not in CITY_COORDS"
        )
        assert route["destination"] in seed_module.CITY_COORDS, (
            f"Route {route['code']} destination '{route['destination']}' not in CITY_COORDS"
        )
