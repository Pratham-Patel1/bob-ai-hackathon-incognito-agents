"""
Tests for ColdChainAnomalyEngine — Phase 2C

Run with:
    pytest src/backend/tests/test_cold_chain_anomaly.py -v
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.engines.cold_chain_anomaly import (
    ColdChainAnalysisResult,
    ExcursionEvent,
    _classify_severity,
    _spoilage_risk,
    analyze_cold_chain,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(base: datetime, offset_mins: float) -> str:
    return (base + timedelta(minutes=offset_mins)).isoformat()


BASE_TIME = datetime(2026, 9, 14, 8, 0, 0, tzinfo=timezone.utc)


def _readings(temps_with_offsets: list[tuple[float, float]]) -> list[dict]:
    """[(temperature, offset_mins_from_base), ...]"""
    return [
        {"timestamp": _ts(BASE_TIME, off), "temperature": temp}
        for temp, off in temps_with_offsets
    ]


# ---------------------------------------------------------------------------
# Severity classification helper
# ---------------------------------------------------------------------------

class TestClassifySeverity:
    def test_no_deviation_is_none(self):
        assert _classify_severity(0.0, 0.0) == "NONE"

    def test_small_deviation_short_duration_is_minor(self):
        assert _classify_severity(1.5, 10.0) == "MINOR"

    def test_deviation_at_minor_max_and_short_duration_is_minor(self):
        assert _classify_severity(2.0, 15.0) == "MINOR"

    def test_deviation_just_above_minor_is_major(self):
        assert _classify_severity(2.1, 10.0) == "MAJOR"

    def test_duration_just_above_minor_is_major(self):
        assert _classify_severity(1.0, 16.0) == "MAJOR"

    def test_deviation_above_major_is_critical(self):
        assert _classify_severity(5.1, 10.0) == "CRITICAL"

    def test_duration_above_major_is_critical(self):
        assert _classify_severity(1.0, 61.0) == "CRITICAL"

    def test_both_critical_thresholds(self):
        assert _classify_severity(6.0, 90.0) == "CRITICAL"


# ---------------------------------------------------------------------------
# Spoilage risk helper
# ---------------------------------------------------------------------------

class TestSpoilageRisk:
    def test_none_severity_is_zero(self):
        assert _spoilage_risk("NONE", 0) == 0.0

    def test_minor_base_is_nonzero(self):
        assert _spoilage_risk("MINOR", 5.0) > 0.0

    def test_critical_base_is_high(self):
        assert _spoilage_risk("CRITICAL", 10.0) >= 85.0

    def test_longer_duration_increases_risk(self):
        r1 = _spoilage_risk("MAJOR", 10.0)
        r2 = _spoilage_risk("MAJOR", 60.0)
        assert r2 > r1

    def test_spoilage_never_exceeds_100(self):
        assert _spoilage_risk("CRITICAL", 999.0) <= 100.0

    def test_spoilage_non_negative(self):
        assert _spoilage_risk("MINOR", 0.0) >= 0.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_readings_no_excursion(self):
        result = analyze_cold_chain([])
        assert isinstance(result, ColdChainAnalysisResult)
        assert result.has_excursion is False
        assert result.excursion_severity == "NONE"

    def test_single_safe_reading_no_excursion(self):
        readings = [{"timestamp": BASE_TIME.isoformat(), "temperature": 5.0}]
        result = analyze_cold_chain(readings)
        assert result.has_excursion is False

    def test_single_excursion_reading(self):
        readings = [{"timestamp": BASE_TIME.isoformat(), "temperature": 12.0}]
        result = analyze_cold_chain(readings)
        assert result.has_excursion is True

    def test_all_safe_readings_no_excursion(self):
        readings = _readings([(3.0, 0), (4.0, 5), (5.0, 10), (6.0, 15)])
        result = analyze_cold_chain(readings)
        assert result.has_excursion is False
        assert result.excursion_severity == "NONE"
        assert result.spoilage_risk_percent == 0.0


# ---------------------------------------------------------------------------
# Severity classification via readings
# ---------------------------------------------------------------------------

class TestSeverityClassification:
    def test_minor_excursion_detection(self):
        """Small deviation, short duration → MINOR"""
        readings = _readings([
            (5.0, 0), (5.0, 5),
            (9.5, 10), (9.5, 18),   # ~1.5°C above 8°C, ~8 mins
            (5.0, 20),
        ])
        result = analyze_cold_chain(readings)
        assert result.has_excursion is True
        assert result.excursion_severity == "MINOR"

    def test_major_excursion_by_deviation(self):
        """Deviation > 2°C → MAJOR"""
        readings = _readings([
            (5.0, 0),
            (11.0, 5), (11.0, 10),  # +3°C above band
            (5.0, 15),
        ])
        result = analyze_cold_chain(readings)
        assert result.excursion_severity in ("MAJOR", "CRITICAL")

    def test_critical_excursion_by_deviation(self):
        """Deviation > 5°C above band → CRITICAL"""
        readings = _readings([
            (5.0, 0),
            (15.0, 5), (15.0, 10),  # +7°C above 8°C band
            (5.0, 15),
        ])
        result = analyze_cold_chain(readings)
        assert result.excursion_severity == "CRITICAL"

    def test_critical_excursion_by_duration(self):
        """Duration > 60 mins → CRITICAL"""
        # Each step is 5 minutes apart, 14 readings = 70 mins
        readings = _readings([(11.0, i * 5) for i in range(15)])
        result = analyze_cold_chain(readings)
        assert result.excursion_severity == "CRITICAL"


# ---------------------------------------------------------------------------
# Custom temperature band
# ---------------------------------------------------------------------------

class TestCustomTemperatureBand:
    def test_frozen_cargo_band(self):
        """Frozen goods band: -20°C to -15°C"""
        cfg = {"temp_min_c": -20.0, "temp_max_c": -15.0}
        readings = _readings([(-18.0, 0), (-18.0, 5), (-10.0, 10), (-10.0, 20), (-18.0, 25)])
        result = analyze_cold_chain(readings, shipment_config=cfg)
        assert result.has_excursion is True

    def test_reading_inside_custom_band_no_excursion(self):
        cfg = {"temp_min_c": -5.0, "temp_max_c": 0.0}
        readings = _readings([(-3.0, 0), (-2.0, 5), (-4.0, 10)])
        result = analyze_cold_chain(readings, shipment_config=cfg)
        assert result.has_excursion is False


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_returns_correct_dataclass(self):
        readings = _readings([(5.0, 0), (5.0, 10)])
        result = analyze_cold_chain(readings)
        assert isinstance(result, ColdChainAnalysisResult)

    def test_max_min_temp_populated(self):
        readings = _readings([(4.0, 0), (6.0, 5), (3.0, 10)])
        result = analyze_cold_chain(readings)
        assert result.max_temp_reached == 6.0
        assert result.min_temp_reached == 3.0

    def test_factors_is_list_of_strings(self):
        result = analyze_cold_chain([])
        assert isinstance(result.factors, list)
        assert all(isinstance(f, str) for f in result.factors)

    def test_excursions_is_list(self):
        readings = _readings([(5.0, 0), (12.0, 5), (5.0, 10)])
        result = analyze_cold_chain(readings)
        assert isinstance(result.excursions, list)

    def test_spoilage_zero_when_no_excursion(self):
        readings = _readings([(4.0, 0), (5.0, 10)])
        result = analyze_cold_chain(readings)
        assert result.spoilage_risk_percent == 0.0

    def test_spoilage_nonzero_when_excursion(self):
        readings = _readings([(5.0, 0), (14.0, 5), (14.0, 10), (5.0, 15)])
        result = analyze_cold_chain(readings)
        assert result.spoilage_risk_percent > 0.0

    def test_deterministic_same_input(self):
        readings = _readings([(5.0, 0), (12.0, 5), (5.0, 20)])
        r1 = analyze_cold_chain(readings)
        r2 = analyze_cold_chain(readings)
        assert r1.excursion_severity == r2.excursion_severity
        assert r1.spoilage_risk_percent == r2.spoilage_risk_percent
