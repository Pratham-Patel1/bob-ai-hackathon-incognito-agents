"""
ShipmentRiskEngine — deterministic weighted-sum risk scoring.

Pure Python — no FastAPI or SQLAlchemy imports.
Aggregates risk across ALL active disruptions for a shipment (via M2M).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RiskFactor:
    name: str
    value: float
    contribution: float  # actual contribution to total score
    weight: float        # defined weight for this factor


@dataclass
class RiskResult:
    score: float           # 0.0–1.0
    level: str             # low | medium | high | critical
    factors: list[RiskFactor] = field(default_factory=list)
    explanation: str = ""


_SEVERITY_MULTIPLIER = {
    "low": 0.5,
    "medium": 0.7,
    "high": 0.9,
    "critical": 1.0,
}


def _level_from_score(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"


def run(
    shipment: dict[str, Any],
    active_disruptions: list[dict[str, Any]],
    temperature_excursion: bool = False,
    carrier: dict[str, Any] | None = None,
) -> RiskResult:
    """
    Calculate deterministic risk score for a shipment.

    Args:
        shipment: dict with keys:
            scheduled_arrival (datetime | str | None),
            cargo_value_usd (float),
            temperature_required (bool)
        active_disruptions: all disruptions currently linked to this
            shipment via shipment_disruptions.  May be empty.
        temperature_excursion: True if any cold-chain excursion is active.
        carrier: dict with key reliability_score (float), or None.

    Returns:
        RiskResult with score clamped to [0.0, 1.0].
    """
    factors: list[RiskFactor] = []
    total = 0.0

    # ── Factor 1: active disruption base ────────────────────────────────────
    DISRUPTION_BASE_WEIGHT = 0.30
    if active_disruptions:
        severities = [d.get("severity", "low") for d in active_disruptions]
        worst = max(severities, key=lambda s: _SEVERITY_MULTIPLIER.get(s, 0))
        multiplier = _SEVERITY_MULTIPLIER.get(worst, 0.5)
        contribution = DISRUPTION_BASE_WEIGHT * multiplier
        total += contribution
        factors.append(
            RiskFactor(
                name="active_disruption",
                value=multiplier,
                contribution=round(contribution, 4),
                weight=DISRUPTION_BASE_WEIGHT,
            )
        )

        # ── Factor 2: compound disruption penalty ───────────────────────────
        if len(active_disruptions) > 1:
            compound = 0.10
            total += compound
            factors.append(
                RiskFactor(
                    name="compound_disruptions",
                    value=float(len(active_disruptions)),
                    contribution=compound,
                    weight=compound,
                )
            )
    else:
        factors.append(
            RiskFactor(
                name="active_disruption",
                value=0.0,
                contribution=0.0,
                weight=DISRUPTION_BASE_WEIGHT,
            )
        )

    # ── Factor 3: urgency (< 24h to arrival) ────────────────────────────────
    URGENCY_WEIGHT = 0.20
    scheduled_arrival = _parse_dt(shipment.get("scheduled_arrival"))
    if scheduled_arrival is not None:
        hours_remaining = (
            scheduled_arrival - datetime.now(timezone.utc)
        ).total_seconds() / 3600
        if hours_remaining < 24:
            urgency_value = max(0.0, 1.0 - hours_remaining / 24.0)
            contribution = URGENCY_WEIGHT * urgency_value
            total += contribution
            factors.append(
                RiskFactor(
                    name="urgency",
                    value=round(urgency_value, 4),
                    contribution=round(contribution, 4),
                    weight=URGENCY_WEIGHT,
                )
            )
        else:
            factors.append(
                RiskFactor(name="urgency", value=0.0, contribution=0.0, weight=URGENCY_WEIGHT)
            )

    # ── Factor 4: high-value cargo ───────────────────────────────────────────
    CARGO_VALUE_WEIGHT = 0.15
    cargo_value = float(shipment.get("cargo_value_usd") or 0)
    if cargo_value > 100_000:
        total += CARGO_VALUE_WEIGHT
        factors.append(
            RiskFactor(
                name="high_value_cargo",
                value=cargo_value,
                contribution=CARGO_VALUE_WEIGHT,
                weight=CARGO_VALUE_WEIGHT,
            )
        )
    else:
        factors.append(
            RiskFactor(name="high_value_cargo", value=cargo_value, contribution=0.0, weight=CARGO_VALUE_WEIGHT)
        )

    # ── Factor 5: cold-chain excursion ───────────────────────────────────────
    COLD_CHAIN_WEIGHT = 0.20
    if shipment.get("temperature_required") and temperature_excursion:
        total += COLD_CHAIN_WEIGHT
        factors.append(
            RiskFactor(
                name="cold_chain_excursion",
                value=1.0,
                contribution=COLD_CHAIN_WEIGHT,
                weight=COLD_CHAIN_WEIGHT,
            )
        )
    else:
        factors.append(
            RiskFactor(name="cold_chain_excursion", value=0.0, contribution=0.0, weight=COLD_CHAIN_WEIGHT)
        )

    # ── Factor 6: carrier reliability ───────────────────────────────────────
    CARRIER_WEIGHT = 0.10
    if carrier is not None:
        reliability = float(carrier.get("reliability_score") or 0.8)
        if reliability < 0.7:
            contribution = CARRIER_WEIGHT * (1.0 - reliability)
            total += contribution
            factors.append(
                RiskFactor(
                    name="carrier_reliability",
                    value=round(reliability, 4),
                    contribution=round(contribution, 4),
                    weight=CARRIER_WEIGHT,
                )
            )
        else:
            factors.append(
                RiskFactor(name="carrier_reliability", value=reliability, contribution=0.0, weight=CARRIER_WEIGHT)
            )
    else:
        factors.append(
            RiskFactor(name="carrier_reliability", value=0.8, contribution=0.0, weight=CARRIER_WEIGHT)
        )

    # Clamp to [0.0, 1.0]
    score = max(0.0, min(1.0, total))
    level = _level_from_score(score)

    # Build explanation from top contributing factors
    top_factors = sorted(factors, key=lambda f: -f.contribution)[:3]
    explanation_parts = []
    for f in top_factors:
        if f.contribution > 0:
            explanation_parts.append(
                f"{f.name.replace('_', ' ')} (+{f.contribution:.2f})"
            )
    explanation = (
        f"Risk score {score:.2f} ({level}). "
        + (
            "Top factors: " + ", ".join(explanation_parts)
            if explanation_parts
            else "No significant risk factors active."
        )
    )

    return RiskResult(
        score=round(score, 4),
        level=level,
        factors=factors,
        explanation=explanation,
    )


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None
