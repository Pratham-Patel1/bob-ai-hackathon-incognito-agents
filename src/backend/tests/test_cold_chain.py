"""
Tests for ColdChainAnomalyEngine.
"""
import pytest
from backend.engines.cold_chain import run, ColdChainAnalysis, _classify_excursion


def _logs(temps: list[float]) -> list[dict]:
    return [{"temperature_c": t} for t in temps]


# ── classify_excursion ────────────────────────────────────────────────────────

def test_classify_minor():
    assert _classify_excursion(1.0, 10.0) == "minor"


def test_classify_major_by_deviation():
    assert _classify_excursion(3.0, 10.0) == "major"


def test_classify_major_by_duration():
    assert _classify_excursion(1.0, 30.0) == "major"


def test_classify_critical_by_deviation():
    assert _classify_excursion(6.0, 5.0) == "critical"


def test_classify_critical_by_duration():
    assert _classify_excursion(1.0, 90.0) == "critical"


# ── run ───────────────────────────────────────────────────────────────────────

def test_no_excursion():
    logs = _logs([2.0, 2.5, 3.0, 2.8, 2.1])
    result = run(logs, temp_min_c=0.0, temp_max_c=8.0)
    assert not result.has_excursion
    assert result.severity == "none"
    assert result.excursion_count == 0


def test_single_minor_excursion():
    # One reading above max (9.0°C when max is 8.0°C) — deviation 1°C, 1 window of 5 min
    logs = _logs([2.0, 2.0, 9.0, 2.0, 2.0])
    result = run(logs, temp_min_c=0.0, temp_max_c=8.0, polling_interval_minutes=5)
    assert result.has_excursion
    assert result.excursion_count == 1
    assert result.severity == "minor"
    assert result.max_deviation_c == pytest.approx(1.0)


def test_critical_excursion_by_deviation():
    # Readings well above max: deviation > 5°C
    logs = _logs([2.0, 15.0, 15.0, 2.0])
    result = run(logs, temp_min_c=0.0, temp_max_c=8.0, polling_interval_minutes=5)
    assert result.has_excursion
    assert result.severity == "critical"
    assert result.max_deviation_c == pytest.approx(7.0)


def test_critical_excursion_by_duration():
    # 15 consecutive out-of-range readings × 5 min = 75 min (> 60 min threshold)
    logs = _logs([2.0] + [10.0] * 15 + [2.0])
    result = run(logs, temp_min_c=0.0, temp_max_c=8.0, polling_interval_minutes=5)
    assert result.has_excursion
    assert result.severity == "critical"
    assert result.total_excursion_minutes >= 75.0


def test_multiple_excursion_windows():
    # Two separate excursion windows
    logs = _logs([2.0, 10.0, 2.0, 2.0, 12.0, 2.0])
    result = run(logs, temp_min_c=0.0, temp_max_c=8.0)
    assert result.excursion_count == 2


def test_empty_logs():
    result = run([], temp_min_c=0.0, temp_max_c=8.0)
    assert not result.has_excursion
    assert result.severity == "none"


def test_critical_recommended_action():
    logs = _logs([2.0, 20.0, 2.0])
    result = run(logs, temp_min_c=0.0, temp_max_c=8.0)
    assert "Expedite" in result.recommended_action


def test_below_min_excursion():
    # Temperature below minimum
    logs = _logs([5.0, -10.0, 5.0])
    result = run(logs, temp_min_c=2.0, temp_max_c=8.0)
    assert result.has_excursion
    assert result.max_deviation_c == pytest.approx(12.0)
