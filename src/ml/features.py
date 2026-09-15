"""
Shared feature extraction for SupplyChainOS risk model.

Used by BOTH the offline training pipeline (train.py) and the inference
engine (predictive_risk.py). Changing this file requires retraining the model.

Feature vector (8 features, in order):
  [0] days_to_scheduled_arrival
  [1] historical_route_delay_rate       (1 - route.reliability_score)
  [2] carrier_reliability_score
  [3] cargo_sensitivity_score           (temperature_sensitive=1.0, hazmat=0.8, fragile=0.6, general=0.3)
  [4] simultaneous_disruption_count
  [5] worst_disruption_severity_encoded (low=1, medium=2, high=3, critical=4; 0 if no disruptions)
  [6] hours_in_transit_pct              (0.0–1.0; how far through the route)
  [7] weight_kg_normalized              (weight_kg / 10000, clamped to [0, 1])
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np

FEATURE_NAMES = [
    "days_to_scheduled_arrival",
    "historical_route_delay_rate",
    "carrier_reliability_score",
    "cargo_sensitivity_score",
    "simultaneous_disruption_count",
    "worst_disruption_severity_encoded",
    "hours_in_transit_pct",
    "weight_kg_normalized",
]

_CARGO_SENSITIVITY = {
    "temperature_sensitive": 1.0,
    "hazmat": 0.8,
    "fragile": 0.6,
    "general": 0.3,
}

_SEVERITY_ENCODING = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def extract_features(
    shipment: dict[str, Any],
    disruptions: list[dict[str, Any]],
    carrier: dict[str, Any],
) -> np.ndarray:
    """
    Extract a feature vector from a shipment, its active disruptions, and carrier.

    Args:
        shipment: dict with keys: scheduled_arrival, scheduled_departure,
                  cargo_type, weight_kg, route_reliability_score (float)
        disruptions: list of dicts with key: severity (str)
        carrier: dict with key: reliability_score (float)

    Returns:
        np.ndarray of shape (8,), dtype float32
    """
    now = _now()

    # [0] days_to_scheduled_arrival
    scheduled_arrival = _parse_dt(shipment.get("scheduled_arrival"))
    if scheduled_arrival is not None:
        delta = (scheduled_arrival - now).total_seconds()
        days_to_arrival = max(0.0, delta / 86400.0)
    else:
        days_to_arrival = 3.0  # fallback

    # [1] historical_route_delay_rate
    route_reliability = float(shipment.get("route_reliability_score", 0.8))
    delay_rate = max(0.0, 1.0 - route_reliability)

    # [2] carrier_reliability_score
    carrier_reliability = float(carrier.get("reliability_score", 0.8))
    carrier_reliability = max(0.0, min(1.0, carrier_reliability))

    # [3] cargo_sensitivity_score
    cargo_type = shipment.get("cargo_type", "general")
    sensitivity = _CARGO_SENSITIVITY.get(cargo_type, 0.3)

    # [4] simultaneous_disruption_count
    disruption_count = float(len(disruptions))

    # [5] worst_disruption_severity_encoded
    if disruptions:
        encoded = max(
            _SEVERITY_ENCODING.get(d.get("severity", "low"), 1) for d in disruptions
        )
    else:
        encoded = 0

    # [6] hours_in_transit_pct (0.0–1.0)
    scheduled_departure = _parse_dt(shipment.get("scheduled_departure"))
    if scheduled_departure is not None and scheduled_arrival is not None:
        total_seconds = (scheduled_arrival - scheduled_departure).total_seconds()
        if total_seconds > 0:
            elapsed = (now - scheduled_departure).total_seconds()
            in_transit_pct = max(0.0, min(1.0, elapsed / total_seconds))
        else:
            in_transit_pct = 0.5
    else:
        in_transit_pct = 0.5  # fallback

    # [7] weight_kg_normalized (clamped 0–1)
    weight_kg = float(shipment.get("weight_kg", 1000.0))
    weight_normalized = min(1.0, weight_kg / 10000.0)

    features = np.array(
        [
            days_to_arrival,
            delay_rate,
            carrier_reliability,
            sensitivity,
            disruption_count,
            float(encoded),
            in_transit_pct,
            weight_normalized,
        ],
        dtype=np.float32,
    )
    return features


def _now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> datetime | None:
    """Parse a datetime from string, datetime object, or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
    return None
