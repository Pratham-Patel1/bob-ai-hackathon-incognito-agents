"""
BusinessImpactEngine — translate delay estimates into financial exposure.

Pure Python — no FastAPI or SQLAlchemy imports.
All rate constants passed explicitly (sourced from config.py in the router).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ShipmentImpact:
    shipment_id: str
    tracking_number: str
    cargo_value_usd: float
    delay_hours: float
    cost_of_delay_usd: float
    sla_breach: bool
    penalty_exposure_usd: float


@dataclass
class BusinessImpact:
    total_cargo_value_at_risk_usd: float
    total_delay_hours: float
    avg_delay_hours: float
    cost_of_delay_usd: float
    penalty_exposure_usd: float
    sla_breach_count: int
    shipment_breakdown: list[ShipmentImpact] = field(default_factory=list)
    explanation: str = ""


def run(
    affected_shipments: list[dict[str, Any]],
    daily_holding_cost_rate: float = 0.002,
    sla_buffer_hours: float = 4.0,
    sla_penalty_usd: float = 5000.0,
) -> BusinessImpact:
    """
    Calculate financial impact for a set of affected shipments.

    Args:
        affected_shipments: list of shipment dicts with keys:
            id, tracking_number, cargo_value_usd (float),
            scheduled_arrival (datetime|str), estimated_arrival (datetime|str|None)
        daily_holding_cost_rate: fraction of cargo value per day delayed (default 0.2%)
        sla_buffer_hours: hours of delay before SLA breach (default 4h)
        sla_penalty_usd: penalty per SLA breach (default $5,000)

    Returns:
        BusinessImpact summary.
    """
    breakdown: list[ShipmentImpact] = []
    total_value = 0.0
    total_delay = 0.0
    total_cost_delay = 0.0
    sla_breaches = 0
    total_penalty = 0.0

    for s in affected_shipments:
        cargo_value = float(s.get("cargo_value_usd") or 0)
        scheduled = _parse_dt(s.get("scheduled_arrival"))
        estimated = _parse_dt(s.get("estimated_arrival"))

        if scheduled is None or estimated is None:
            delay_hours = 0.0
        else:
            delay_seconds = (estimated - scheduled).total_seconds()
            delay_hours = max(0.0, delay_seconds / 3600.0)

        cost_of_delay = (delay_hours / 24.0) * cargo_value * daily_holding_cost_rate
        sla_breach = delay_hours > sla_buffer_hours
        penalty = sla_penalty_usd if sla_breach else 0.0

        total_value += cargo_value
        total_delay += delay_hours
        total_cost_delay += cost_of_delay
        if sla_breach:
            sla_breaches += 1
            total_penalty += penalty

        breakdown.append(
            ShipmentImpact(
                shipment_id=str(s["id"]),
                tracking_number=str(s.get("tracking_number") or s["id"]),
                cargo_value_usd=round(cargo_value, 2),
                delay_hours=round(delay_hours, 2),
                cost_of_delay_usd=round(cost_of_delay, 2),
                sla_breach=sla_breach,
                penalty_exposure_usd=round(penalty, 2),
            )
        )

    n = len(breakdown)
    avg_delay = total_delay / n if n > 0 else 0.0

    explanation = (
        f"{n} shipments affected. "
        f"Total cargo value at risk: ${total_value:,.0f}. "
        f"Estimated cost of delay: ${total_cost_delay:,.0f}. "
        f"SLA breaches: {sla_breaches} (penalty exposure: ${total_penalty:,.0f}). "
        f"Avg delay: {avg_delay:.1f}h."
    )

    return BusinessImpact(
        total_cargo_value_at_risk_usd=round(total_value, 2),
        total_delay_hours=round(total_delay, 2),
        avg_delay_hours=round(avg_delay, 2),
        cost_of_delay_usd=round(total_cost_delay, 2),
        penalty_exposure_usd=round(total_penalty, 2),
        sla_breach_count=sla_breaches,
        shipment_breakdown=breakdown,
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
