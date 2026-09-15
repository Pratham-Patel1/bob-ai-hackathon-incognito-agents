"""Geo utility tests."""
from backend.utils.geo import haversine


def test_haversine_same_point() -> None:
    assert haversine(52.0, 13.0, 52.0, 13.0) == 0.0


def test_haversine_hamburg_frankfurt() -> None:
    # Hamburg (53.55, 9.99) to Frankfurt (50.11, 8.68)
    dist = haversine(53.55, 9.99, 50.11, 8.68)
    # ~490km road distance; great-circle ~390km
    assert 350 < dist < 420, f"Expected ~390km, got {dist:.1f}km"


def test_haversine_known_pair() -> None:
    # New York to London: ~5570km
    dist = haversine(40.71, -74.01, 51.51, -0.13)
    assert 5400 < dist < 5700, f"Expected ~5570km, got {dist:.1f}km"
