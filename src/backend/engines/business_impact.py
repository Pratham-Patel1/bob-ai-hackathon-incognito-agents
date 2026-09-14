"""
BusinessImpactEngine — Phase 2E

Computes the total financial exposure for a disrupted shipment:

    Total Financial Exposure = Cargo Value at Risk
                             + SLA Penalty
                             + Extra Transport Cost

Input contract
--------------
No ORM / DB access inside this file.
The router/service layer passes plain dicts.

shipment : dict
    cargo_value_usd         float   declared cargo value
    cargo_type              str     "general"|"temperature_sensitive"|"hazmat"|"fragile"
    temperature_required    bool
    weight_kg               float
    priority                str     "low"|"medium"|"high"|"critical"
    scheduled_arrival       str | datetime
    estimated_arrival       str | datetime

disruption_context : dict | None
    delay_hours             float   estimated extra delay
    severity                str     "low"|"medium"|"high"|"critical"
    disruption_type         str     "weather"|"port_closure"|"customs"|"mechanical"|"other"

alternative_route_cost_usd : float | None
    Extra cost if rerouted (from RouteOptimizationEngine result)

Output
------
BusinessImpactResult dataclass:
    cargo_value_at_risk_usd     float
    sla_penalty_usd             float
    extra_transport_cost_usd    float
    total_financial_exposure_usd float
    risk_percentage             float   exposure as % of cargo value
    breakdown                   dict    named components
    factors                     list[str]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# SLA penalty rates by priority (% of cargo value per hour of delay)
# ---------------------------------------------------------------------------

_SLA_PENALTY_RATE_PER_HOUR: Dict[str, float] = {
    "low":      0.0005,   # 0.05% per hour
    "medium":   0.0010,   # 0.10% per hour
    "high":     0.0020,   # 0.20% per hour
    "critical": 0.0050,   # 0.50% per hour
}

# SLA penalty cap (% of cargo value)
_SLA_PENALTY_CAP_PCT = 0.25    # max 25% of cargo value

# ---------------------------------------------------------------------------
# Cargo risk exposure rates (% of cargo value at risk per delay hour)
# ---------------------------------------------------------------------------

_CARGO_RISK_RATE: Dict[str, float] = {
    "general":               0.001,   # 0.1%/hr
    "temperature_sensitive": 0.010,   # 1%/hr (spoilage risk)
    "hazmat":                0.005,   # 0.5%/hr
    "fragile":               0.003,   # 0.3%/hr
}

# Cargo at risk cap (% of cargo value)
_CARGO_RISK_CAP_PCT = 0.80   # max 80% at risk

# ---------------------------------------------------------------------------
# Extra transport cost multipliers when rerouting
# (applied to alternative_route_cost if not directly provided)
# ---------------------------------------------------------------------------

_REROUTE_MULTIPLIER: Dict[str, float] = {
    "low":      1.05,
    "medium":   1.15,
    "high":     1.35,
    "critical": 1.60,
}


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class BusinessImpactResult:
    cargo_value_at_risk_usd: float
    sla_penalty_usd: float
    extra_transport_cost_usd: float
    total_financial_exposure_usd: float
    risk_percentage: float           # exposure / cargo_value * 100
    breakdown: Dict[str, float]
    factors: List[str]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def calculate_business_impact(
    shipment: Dict[str, Any],
    disruption_context: Optional[Dict[str, Any]] = None,
    alternative_route_cost_usd: Optional[float] = None,
) -> BusinessImpactResult:
    """
    Calculate total financial exposure for a disrupted shipment.

    Parameters
    ----------
    shipment : dict
        Shipment record fields (plain dict).
    disruption_context : dict | None
        Details of the disruption causing the impact.
    alternative_route_cost_usd : float | None
        Rerouting cost from RouteOptimizationEngine. If None, estimated
        from severity multiplier applied to base transport cost.

    Returns
    -------
    BusinessImpactResult
    """
    ctx = disruption_context or {}
    factors: List[str] = []

    cargo_value  = float(shipment.get("cargo_value_usd") or 0.0)
    cargo_type   = str(shipment.get("cargo_type") or "general").lower()
    temp_req     = bool(shipment.get("temperature_required") or False)
    priority     = str(shipment.get("priority") or "medium").lower()

    delay_hours  = float(ctx.get("delay_hours") or 0.0)
    severity     = str(ctx.get("severity") or "medium").lower()
    dis_type     = str(ctx.get("disruption_type") or "other").lower()

    # Resolve cargo type for temperature-sensitive check
    effective_cargo_type = cargo_type
    if temp_req and effective_cargo_type == "general":
        effective_cargo_type = "temperature_sensitive"

    # ------------------------------------------------------------------
    # 1. Cargo Value at Risk
    # ------------------------------------------------------------------
    cargo_risk_rate = _CARGO_RISK_RATE.get(effective_cargo_type, _CARGO_RISK_RATE["general"])
    cargo_at_risk_raw = cargo_value * cargo_risk_rate * delay_hours
    cargo_at_risk = round(min(cargo_at_risk_raw, cargo_value * _CARGO_RISK_CAP_PCT), 2)

    # ------------------------------------------------------------------
    # 2. SLA Penalty
    # ------------------------------------------------------------------
    sla_rate = _SLA_PENALTY_RATE_PER_HOUR.get(priority, _SLA_PENALTY_RATE_PER_HOUR["medium"])
    sla_penalty_raw = cargo_value * sla_rate * delay_hours
    sla_penalty = round(min(sla_penalty_raw, cargo_value * _SLA_PENALTY_CAP_PCT), 2)

    # ------------------------------------------------------------------
    # 3. Extra Transport Cost (rerouting)
    # ------------------------------------------------------------------
    if alternative_route_cost_usd is not None:
        extra_transport = round(float(alternative_route_cost_usd), 2)
    else:
        # Estimate from base transport cost proxy
        # Use weight_kg * 0.5 USD/kg as baseline transport cost
        weight_kg = float(shipment.get("weight_kg") or 100.0)
        base_transport = weight_kg * 0.5
        multiplier = _REROUTE_MULTIPLIER.get(severity, _REROUTE_MULTIPLIER["medium"])
        extra_transport = round(base_transport * (multiplier - 1.0), 2)

    # ------------------------------------------------------------------
    # 4. Total Exposure
    # ------------------------------------------------------------------
    total_exposure = round(cargo_at_risk + sla_penalty + extra_transport, 2)
    risk_pct = round((total_exposure / cargo_value * 100.0) if cargo_value > 0 else 0.0, 1)

    # ------------------------------------------------------------------
    # Breakdown dict
    # ------------------------------------------------------------------
    breakdown = {
        "cargo_value_at_risk_usd":   cargo_at_risk,
        "sla_penalty_usd":           sla_penalty,
        "extra_transport_cost_usd":  extra_transport,
        "total_financial_exposure_usd": total_exposure,
    }

    # ------------------------------------------------------------------
    # Factors
    # ------------------------------------------------------------------
    factors.append(f"Cargo value: ${cargo_value:,.2f} | Type: {effective_cargo_type} | Priority: {priority.upper()}")
    factors.append(f"Disruption: {dis_type.replace('_', ' ')} | Severity: {severity.upper()} | Delay: {delay_hours:.1f}h")
    factors.append(
        f"Cargo at risk: ${cargo_at_risk:,.2f} "
        f"(rate {cargo_risk_rate*100:.1f}%/h × {delay_hours:.1f}h)"
    )
    factors.append(
        f"SLA penalty: ${sla_penalty:,.2f} "
        f"(rate {sla_rate*100:.2f}%/h × {delay_hours:.1f}h, "
        f"cap {_SLA_PENALTY_CAP_PCT*100:.0f}% of cargo value)"
    )
    factors.append(
        f"Extra transport cost: ${extra_transport:,.2f} "
        f"({'provided by route optimizer' if alternative_route_cost_usd is not None else 'estimated from severity multiplier'})"
    )
    factors.append(
        f"Total financial exposure: ${total_exposure:,.2f} "
        f"({risk_pct:.1f}% of cargo value)"
    )

    return BusinessImpactResult(
        cargo_value_at_risk_usd=cargo_at_risk,
        sla_penalty_usd=sla_penalty,
        extra_transport_cost_usd=extra_transport,
        total_financial_exposure_usd=total_exposure,
        risk_percentage=risk_pct,
        breakdown=breakdown,
        factors=factors,
    )
