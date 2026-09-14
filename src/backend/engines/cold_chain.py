"""
ColdChainAnomalyEngine — temperature excursion detection and classification.

Pure Python — no FastAPI or SQLAlchemy imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExcursionWindow:
    """A contiguous block of out-of-range readings."""
    start_idx: int
    end_idx: int
    max_deviation_c: float
    duration_minutes: float
    severity: str  # minor | major | critical


@dataclass
class ColdChainAnalysis:
    has_excursion: bool
    severity: str                    # none | minor | major | critical
    excursion_count: int
    max_deviation_c: float
    total_excursion_minutes: float
    recommended_action: str
    explanation: str
    excursion_windows: list[ExcursionWindow] = field(default_factory=list)


_POLLING_INTERVAL_MINUTES = 5.0   # default sensor polling interval


def _classify_excursion(deviation_c: float, duration_minutes: float) -> str:
    """
    Severity classification:
      minor   — deviation ≤ 2°C AND duration ≤ 15 min
      major   — deviation 2–5°C OR duration 15–60 min
      critical — deviation > 5°C OR duration > 60 min
    """
    if deviation_c > 5.0 or duration_minutes > 60.0:
        return "critical"
    if deviation_c > 2.0 or duration_minutes > 15.0:
        return "major"
    return "minor"


def _worst_severity(*severities: str) -> str:
    order = {"none": 0, "minor": 1, "major": 2, "critical": 3}
    return max(severities, key=lambda s: order.get(s, 0))


def run(
    temperature_logs: list[dict[str, Any]],
    temp_min_c: float,
    temp_max_c: float,
    polling_interval_minutes: float = _POLLING_INTERVAL_MINUTES,
) -> ColdChainAnalysis:
    """
    Analyse a sequence of temperature log records for excursions.

    Args:
        temperature_logs: list of dicts with keys:
            temperature_c (float), recorded_at (str | datetime)
            Assumed to be sorted by recorded_at ascending.
        temp_min_c: lower bound of acceptable temperature range.
        temp_max_c: upper bound of acceptable temperature range.
        polling_interval_minutes: minutes between readings (default 5).

    Returns:
        ColdChainAnalysis.
    """
    if not temperature_logs:
        return ColdChainAnalysis(
            has_excursion=False,
            severity="none",
            excursion_count=0,
            max_deviation_c=0.0,
            total_excursion_minutes=0.0,
            recommended_action="No action required.",
            explanation="No temperature readings available.",
        )

    windows: list[ExcursionWindow] = []
    in_excursion = False
    window_start = 0
    max_dev_in_window = 0.0

    for i, log in enumerate(temperature_logs):
        temp = float(log["temperature_c"])
        deviation = 0.0
        if temp < temp_min_c:
            deviation = temp_min_c - temp
        elif temp > temp_max_c:
            deviation = temp - temp_max_c

        is_out = temp < temp_min_c or temp > temp_max_c

        if is_out and not in_excursion:
            in_excursion = True
            window_start = i
            max_dev_in_window = deviation
        elif is_out and in_excursion:
            max_dev_in_window = max(max_dev_in_window, deviation)
        elif not is_out and in_excursion:
            # Window ended at i-1
            duration = (i - window_start) * polling_interval_minutes
            severity = _classify_excursion(max_dev_in_window, duration)
            windows.append(
                ExcursionWindow(
                    start_idx=window_start,
                    end_idx=i - 1,
                    max_deviation_c=round(max_dev_in_window, 2),
                    duration_minutes=round(duration, 1),
                    severity=severity,
                )
            )
            in_excursion = False
            max_dev_in_window = 0.0

    # Close any open window at end of data
    if in_excursion:
        duration = (len(temperature_logs) - window_start) * polling_interval_minutes
        severity = _classify_excursion(max_dev_in_window, duration)
        windows.append(
            ExcursionWindow(
                start_idx=window_start,
                end_idx=len(temperature_logs) - 1,
                max_deviation_c=round(max_dev_in_window, 2),
                duration_minutes=round(duration, 1),
                severity=severity,
            )
        )

    if not windows:
        return ColdChainAnalysis(
            has_excursion=False,
            severity="none",
            excursion_count=0,
            max_deviation_c=0.0,
            total_excursion_minutes=0.0,
            recommended_action="Temperature within acceptable range throughout transit.",
            explanation=(
                f"All {len(temperature_logs)} readings within "
                f"[{temp_min_c}°C, {temp_max_c}°C]."
            ),
            excursion_windows=[],
        )

    total_minutes = sum(w.duration_minutes for w in windows)
    max_dev = max(w.max_deviation_c for w in windows)
    worst = _worst_severity(*[w.severity for w in windows])

    # Recommended action based on worst severity
    if worst == "critical":
        action = (
            "Expedite to destination immediately. Notify QA team. "
            "Quarantine cargo on arrival for quality assessment."
        )
    elif worst == "major":
        action = (
            "Notify receiving team. Inspect cargo on arrival. "
            "Document excursion for compliance records."
        )
    else:
        action = (
            "Log excursion for compliance records. "
            "Monitor remaining transit."
        )

    explanation = (
        f"{len(windows)} excursion window(s) detected. "
        f"Worst severity: {worst}. "
        f"Max deviation: {max_dev:.1f}°C from range [{temp_min_c}, {temp_max_c}]°C. "
        f"Total excursion time: {total_minutes:.0f} minutes."
    )

    return ColdChainAnalysis(
        has_excursion=True,
        severity=worst,
        excursion_count=len(windows),
        max_deviation_c=round(max_dev, 2),
        total_excursion_minutes=round(total_minutes, 1),
        recommended_action=action,
        explanation=explanation,
        excursion_windows=windows,
    )
