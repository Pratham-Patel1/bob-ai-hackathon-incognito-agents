"""
Synthetic training data generator for the SupplyChainOS risk model.

Generates ~5,000 labelled historical shipment records.
Label: was_delayed (1 = delayed >4h from scheduled arrival, 0 = on time)

Output: src/ml/training_data.csv (gitignored — only the artifact is committed)

Usage:
    python src/ml/generate_training_data.py
"""
from __future__ import annotations

import csv
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running from repo root or from src/ml/
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np

RANDOM_SEED = 42
N_RECORDS = 5000
OUTPUT_PATH = Path(__file__).parent / "training_data.csv"

CARRIER_RELIABILITY_RANGE = (0.50, 0.99)
ROUTE_RELIABILITY_RANGE = (0.55, 0.98)
CARGO_TYPES = ["general", "temperature_sensitive", "hazmat", "fragile"]
SEVERITIES = ["low", "medium", "high", "critical"]

FIELDNAMES = [
    "days_to_scheduled_arrival",
    "historical_route_delay_rate",
    "carrier_reliability_score",
    "cargo_sensitivity_score",
    "simultaneous_disruption_count",
    "worst_disruption_severity_encoded",
    "hours_in_transit_pct",
    "weight_kg_normalized",
    "was_delayed",
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


def _inject_label(
    carrier_reliability: float,
    route_delay_rate: float,
    disruption_count: int,
    worst_severity: str,
    days_to_arrival: float,
    rng: random.Random,
) -> int:
    """Deterministic label injection with controlled probabilities."""
    # Rule 1: Poor carrier + high disruption severity → very likely delayed
    if carrier_reliability < 0.6 and worst_severity in ("high", "critical"):
        return 1 if rng.random() < 0.85 else 0

    # Rule 2: Urgency + multiple disruptions → likely delayed
    if days_to_arrival < 1.0 and disruption_count > 1:
        return 1 if rng.random() < 0.80 else 0

    # Rule 3: Any disruption at high/critical + moderate carrier → likely delayed
    if worst_severity in ("high", "critical") and carrier_reliability < 0.80:
        return 1 if rng.random() < 0.65 else 0

    # Rule 4: Route is unreliable (high delay rate)
    if route_delay_rate > 0.35:
        return 1 if rng.random() < 0.55 else 0

    # Default: Bernoulli draw from route delay rate
    return 1 if rng.random() < route_delay_rate else 0


def generate_record(rng: random.Random, numpy_rng: np.random.Generator) -> dict:
    """Generate a single synthetic historical shipment record."""
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Carrier
    carrier_reliability = round(rng.uniform(*CARRIER_RELIABILITY_RANGE), 4)

    # Route
    route_reliability = round(rng.uniform(*ROUTE_RELIABILITY_RANGE), 4)
    route_delay_rate = round(1.0 - route_reliability, 4)

    # Cargo
    cargo_type = rng.choice(CARGO_TYPES)
    sensitivity = _CARGO_SENSITIVITY[cargo_type]

    # Weight
    weight_kg = round(rng.uniform(50, 25000), 2)
    weight_normalized = min(1.0, weight_kg / 10000.0)

    # Disruptions
    disruption_count = numpy_rng.choice(
        [0, 1, 2, 3], p=[0.45, 0.35, 0.15, 0.05]
    )
    if disruption_count > 0:
        severities_drawn = [rng.choice(SEVERITIES) for _ in range(disruption_count)]
        worst_severity = max(severities_drawn, key=lambda s: _SEVERITY_ENCODING[s])
        worst_severity_encoded = _SEVERITY_ENCODING[worst_severity]
    else:
        worst_severity = "low"
        worst_severity_encoded = 0

    # Days to arrival (historical — how far out when we look at the shipment)
    days_to_arrival = round(rng.uniform(0.1, 14.0), 2)

    # In-transit percent
    in_transit_pct = round(rng.uniform(0.0, 1.0), 4)

    # Label
    was_delayed = _inject_label(
        carrier_reliability,
        route_delay_rate,
        disruption_count,
        worst_severity,
        days_to_arrival,
        rng,
    )

    return {
        "days_to_scheduled_arrival": days_to_arrival,
        "historical_route_delay_rate": route_delay_rate,
        "carrier_reliability_score": carrier_reliability,
        "cargo_sensitivity_score": sensitivity,
        "simultaneous_disruption_count": disruption_count,
        "worst_disruption_severity_encoded": worst_severity_encoded,
        "hours_in_transit_pct": in_transit_pct,
        "weight_kg_normalized": weight_normalized,
        "was_delayed": was_delayed,
    }


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    numpy_rng = np.random.default_rng(RANDOM_SEED)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    records = [generate_record(rng, numpy_rng) for _ in range(N_RECORDS)]

    delayed_count = sum(r["was_delayed"] for r in records)
    print(f"Generated {N_RECORDS} records")
    print(f"  Delayed: {delayed_count} ({delayed_count / N_RECORDS * 100:.1f}%)")
    print(f"  On time: {N_RECORDS - delayed_count}")

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)

    print(f"Written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
