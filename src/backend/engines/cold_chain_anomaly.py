"""
ColdChainAnomalyEngine — Phase 2C

Detects temperature excursions in cold-chain shipment IoT sensor logs
and classifies their severity as MINOR, MAJOR, or CRITICAL.

Input contract
--------------
No ORM / DB access inside this file.
The router passes a list of temperature reading dicts and a shipment config dict.

temperature_readings : list of dicts
    Each dict must have:
        timestamp   str | datetime   ISO-8601 or datetime object
        temperature float            degrees Celsius
        humidity    float | None     optional, percent

shipment_config : dict
    temp_min_c  float   lower bound of safe temperature range (default 2.0)
    temp_max_c  float   upper bound of safe temperature range (default 8.0)
    cargo_type  str     e.g. "temperature_sensitive", "vaccine", "frozen"

Output
------
ColdChainAnalysisResult dataclass:
    has_excursion           bool
    excursion_severity      str     NONE | MINOR | MAJOR | CRITICAL
    max_temp_reached        float
    min_temp_reached        float
    excursion_duration_mins float   total minutes outside safe range
    spoilage_risk_percent   float   0–100 estimated spoilage probability
    excursions              list[ExcursionEvent]  individual events
    factors                 list[str] human-readable explanation

Severity classification:
    MINOR    deviation <= 2°C  AND  duration <= 15 mins
    MAJOR    deviation 2–5°C   OR   duration 15–60 mins
    CRITICAL deviation > 5°C   OR   duration > 60 mins
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Default safe temperature band (pharmaceutical cold chain)
# ---------------------------------------------------------------------------

DEFAULT_TEMP_MIN_C = 2.0
DEFAULT_TEMP_MAX_C = 8.0

# ---------------------------------------------------------------------------
# Severity thresholds
# ---------------------------------------------------------------------------

_DEVIATION_MINOR_MAX = 2.0       # °C above/below band edge
_DEVIATION_MAJOR_MAX = 5.0       # °C above/below band edge — beyond is CRITICAL

_DURATION_MINOR_MAX_MINS = 15.0
_DURATION_MAJOR_MAX_MINS = 60.0

# ---------------------------------------------------------------------------
# Spoilage risk table  (severity -> base %)
# ---------------------------------------------------------------------------

_SPOILAGE_BASE: Dict[str, float] = {
    "NONE":     0.0,
    "MINOR":   10.0,
    "MAJOR":   40.0,
    "CRITICAL": 85.0,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExcursionEvent:
    start_time: str
    end_time: str
    max_deviation_c: float
    duration_mins: float
    severity: str


@dataclass
class ColdChainAnalysisResult:
    has_excursion: bool
    excursion_severity: str          # NONE | MINOR | MAJOR | CRITICAL
    max_temp_reached: float
    min_temp_reached: float
    excursion_duration_mins: float
    spoilage_risk_percent: float
    excursions: List[ExcursionEvent]
    factors: List[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _classify_severity(max_deviation_c: float, total_duration_mins: float) -> str:
    """
    Classify overall excursion severity from worst-case deviation and total duration.
    CRITICAL wins if either threshold is exceeded.
    """
    if max_deviation_c <= 0 and total_duration_mins <= 0:
        return "NONE"
    if max_deviation_c > _DEVIATION_MAJOR_MAX or total_duration_mins > _DURATION_MAJOR_MAX_MINS:
        return "CRITICAL"
    if max_deviation_c > _DEVIATION_MINOR_MAX or total_duration_mins > _DURATION_MINOR_MAX_MINS:
        return "MAJOR"
    return "MINOR"


def _classify_event_severity(deviation: float, duration_mins: float) -> str:
    if deviation > _DEVIATION_MAJOR_MAX or duration_mins > _DURATION_MAJOR_MAX_MINS:
        return "CRITICAL"
    if deviation > _DEVIATION_MINOR_MAX or duration_mins > _DURATION_MINOR_MAX_MINS:
        return "MAJOR"
    return "MINOR"


def _spoilage_risk(severity: str, duration_mins: float) -> float:
    """
    Estimate spoilage risk percentage.
    Duration multiplier applies a proportional increase for extended exposures.
    """
    base = _SPOILAGE_BASE.get(severity, 0.0)
    if severity == "NONE":
        return 0.0
    # Duration multiplier: each hour beyond threshold adds proportional risk
    if severity == "MINOR":
        extra = min(duration_mins / _DURATION_MINOR_MAX_MINS, 3.0) * 5.0
    elif severity == "MAJOR":
        extra = min(duration_mins / _DURATION_MAJOR_MAX_MINS, 3.0) * 15.0
    else:  # CRITICAL
        extra = min(duration_mins / 120.0, 1.0) * 15.0
    return round(min(base + extra, 100.0), 1)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def analyze_cold_chain(
    temperature_readings: List[Dict[str, Any]],
    shipment_config: Optional[Dict[str, Any]] = None,
) -> ColdChainAnalysisResult:
    """
    Analyse temperature readings for a cold-chain shipment.

    Parameters
    ----------
    temperature_readings : list of dicts
        Each entry: {"timestamp": ..., "temperature": float, "humidity": float|None}
    shipment_config : dict | None
        Optional keys: temp_min_c, temp_max_c, cargo_type

    Returns
    -------
    ColdChainAnalysisResult
    """
    cfg = shipment_config or {}
    temp_min = float(cfg.get("temp_min_c") or DEFAULT_TEMP_MIN_C)
    temp_max = float(cfg.get("temp_max_c") or DEFAULT_TEMP_MAX_C)
    factors: List[str] = []

    # ------------------------------------------------------------------
    # Edge case — no readings
    # ------------------------------------------------------------------
    if not temperature_readings:
        return ColdChainAnalysisResult(
            has_excursion=False,
            excursion_severity="NONE",
            max_temp_reached=0.0,
            min_temp_reached=0.0,
            excursion_duration_mins=0.0,
            spoilage_risk_percent=0.0,
            excursions=[],
            factors=["No temperature readings available"],
        )

    # ------------------------------------------------------------------
    # Sort readings by timestamp
    # ------------------------------------------------------------------
    parsed: List[tuple[datetime, float]] = []
    for r in temperature_readings:
        dt = _to_datetime(r.get("timestamp"))
        temp = r.get("temperature")
        if dt is not None and temp is not None:
            parsed.append((dt, float(temp)))

    if not parsed:
        return ColdChainAnalysisResult(
            has_excursion=False,
            excursion_severity="NONE",
            max_temp_reached=0.0,
            min_temp_reached=0.0,
            excursion_duration_mins=0.0,
            spoilage_risk_percent=0.0,
            excursions=[],
            factors=["Temperature readings could not be parsed"],
        )

    parsed.sort(key=lambda x: x[0])
    temps = [t for _, t in parsed]

    max_temp = max(temps)
    min_temp = min(temps)

    # ------------------------------------------------------------------
    # Identify excursion windows
    # ------------------------------------------------------------------
    excursion_events: List[ExcursionEvent] = []
    total_excursion_mins = 0.0
    max_deviation = 0.0

    in_excursion = False
    excursion_start: Optional[datetime] = None
    excursion_peak_dev = 0.0

    for i, (dt, temp) in enumerate(parsed):
        is_out_of_range = temp < temp_min or temp > temp_max
        deviation = max(temp_min - temp, 0.0) + max(temp - temp_max, 0.0)

        if is_out_of_range:
            if not in_excursion:
                in_excursion = True
                excursion_start = dt
                excursion_peak_dev = deviation
            else:
                excursion_peak_dev = max(excursion_peak_dev, deviation)
            max_deviation = max(max_deviation, deviation)
        else:
            if in_excursion:
                # Close the excursion window
                prev_dt, _ = parsed[i - 1]
                duration = (prev_dt - excursion_start).total_seconds() / 60.0
                total_excursion_mins += duration
                sev = _classify_event_severity(excursion_peak_dev, duration)
                excursion_events.append(ExcursionEvent(
                    start_time=excursion_start.isoformat(),
                    end_time=prev_dt.isoformat(),
                    max_deviation_c=round(excursion_peak_dev, 2),
                    duration_mins=round(duration, 1),
                    severity=sev,
                ))
                in_excursion = False
                excursion_peak_dev = 0.0

    # Handle open excursion at end of readings
    if in_excursion and excursion_start is not None:
        last_dt, _ = parsed[-1]
        duration = (last_dt - excursion_start).total_seconds() / 60.0
        total_excursion_mins += max(duration, 0.0)
        sev = _classify_event_severity(excursion_peak_dev, duration)
        excursion_events.append(ExcursionEvent(
            start_time=excursion_start.isoformat(),
            end_time=last_dt.isoformat(),
            max_deviation_c=round(excursion_peak_dev, 2),
            duration_mins=round(total_excursion_mins, 1),
            severity=sev,
        ))

    # ------------------------------------------------------------------
    # Overall classification
    # ------------------------------------------------------------------
    has_excursion = len(excursion_events) > 0
    overall_severity = _classify_severity(max_deviation, total_excursion_mins) if has_excursion else "NONE"
    spoilage = _spoilage_risk(overall_severity, total_excursion_mins)

    # ------------------------------------------------------------------
    # Build factors
    # ------------------------------------------------------------------
    factors.append(f"Safe temperature band: {temp_min}°C – {temp_max}°C")
    factors.append(f"Sensor range observed: {min_temp:.1f}°C – {max_temp:.1f}°C")

    if has_excursion:
        factors.append(
            f"{len(excursion_events)} excursion event(s) detected — "
            f"total {total_excursion_mins:.1f} minutes outside safe range"
        )
        factors.append(f"Maximum deviation from safe band: {max_deviation:.2f}°C")
        factors.append(f"Overall severity: {overall_severity}")
        factors.append(f"Estimated spoilage risk: {spoilage:.1f}%")
    else:
        factors.append("No temperature excursions detected — cargo integrity maintained")

    return ColdChainAnalysisResult(
        has_excursion=has_excursion,
        excursion_severity=overall_severity,
        max_temp_reached=round(max_temp, 2),
        min_temp_reached=round(min_temp, 2),
        excursion_duration_mins=round(total_excursion_mins, 1),
        spoilage_risk_percent=spoilage,
        excursions=excursion_events,
        factors=factors,
    )
