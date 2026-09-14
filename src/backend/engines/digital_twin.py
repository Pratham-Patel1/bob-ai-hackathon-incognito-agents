"""
DigitalTwinEngine — Phase 2E

Performs in-memory what-if simulation comparing a CURRENT shipment
scenario against a SIMULATED alternative (e.g. route swap, carrier change).

Architecture rules:
  - MUST NOT write to the database — pure read + compute only
  - No ORM / DB access inside this file
  - All inputs are plain dicts passed by the router/service layer

Input contract
--------------
current_scenario : dict
    Snapshot of the real, live shipment state:
        shipment_id          str
        tracking_number      str
        current_route_id     str
        current_carrier_id   str
        estimated_hours      float   ETA in hours from now
        total_cost_usd       float   current transport cost
        risk_score           float   current combined risk score (0–100)
        risk_level           str     LOW|MEDIUM|HIGH|CRITICAL
        on_time_probability  float   0.0–1.0

simulated_changes : dict
    The proposed alternative (only changed fields needed):
        simulated_route_id           str | None
        simulated_carrier_id         str | None
        simulated_estimated_hours    float | None
        simulated_total_cost_usd     float | None
        simulated_risk_score         float | None
        simulated_on_time_probability float | None

Output
------
DigitalTwinResult dataclass:
    current    ScenarioSnapshot
    simulated  ScenarioSnapshot
    delta      ScenarioDelta   (simulated - current)
    recommendation  str        "SWITCH" | "KEEP"
    confidence      float      0.0–1.0
    factors         list[str]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ScenarioSnapshot:
    shipment_id: str
    tracking_number: str
    route_id: str
    carrier_id: str
    estimated_hours: float
    total_cost_usd: float
    risk_score: float
    risk_level: str
    on_time_probability: float


@dataclass
class ScenarioDelta:
    hours_delta: float            # simulated - current (negative = faster)
    cost_delta_usd: float         # simulated - current (negative = cheaper)
    risk_score_delta: float       # simulated - current (negative = lower risk)
    on_time_delta: float          # simulated - current (positive = better)
    hours_change_pct: float
    cost_change_pct: float
    risk_change_pct: float


@dataclass
class DigitalTwinResult:
    current: ScenarioSnapshot
    simulated: ScenarioSnapshot
    delta: ScenarioDelta
    recommendation: str           # "SWITCH" | "KEEP"
    confidence: float             # 0.0–1.0
    factors: List[str]


# ---------------------------------------------------------------------------
# Risk level helper
# ---------------------------------------------------------------------------

_RISK_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _risk_level_from_score(score: float) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def _safe_pct(new: float, old: float) -> float:
    """Percentage change; returns 0.0 if old == 0."""
    if old == 0:
        return 0.0
    return round((new - old) / abs(old) * 100.0, 1)


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def _compute_confidence(delta: ScenarioDelta, simulated: ScenarioSnapshot) -> float:
    """
    Estimate confidence (0–1) that switching to the simulated route is beneficial.
    Based on how many dimensions improve and by how much.
    """
    score = 0.0
    weights = {"risk": 0.40, "on_time": 0.35, "cost": 0.15, "hours": 0.10}

    # Risk improvement
    if delta.risk_score_delta < 0:
        risk_improvement = min(abs(delta.risk_score_delta) / 50.0, 1.0)
        score += weights["risk"] * risk_improvement

    # On-time improvement
    if delta.on_time_delta > 0:
        score += weights["on_time"] * min(delta.on_time_delta / 0.30, 1.0)

    # Cost improvement
    if delta.cost_delta_usd < 0:
        cost_improvement = min(abs(delta.cost_change_pct) / 30.0, 1.0)
        score += weights["cost"] * cost_improvement

    # ETA improvement
    if delta.hours_delta < 0:
        eta_improvement = min(abs(delta.hours_change_pct) / 20.0, 1.0)
        score += weights["hours"] * eta_improvement

    # Penalty if simulated risk is still CRITICAL
    if simulated.risk_level == "CRITICAL":
        score *= 0.5

    return round(min(score, 1.0), 3)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def run_digital_twin(
    current_scenario: Dict[str, Any],
    simulated_changes: Dict[str, Any],
) -> DigitalTwinResult:
    """
    Compare current vs simulated scenario in-memory.

    Parameters
    ----------
    current_scenario : dict
        Live shipment state snapshot.
    simulated_changes : dict
        Only the fields that change in the simulated scenario.
        Unchanged fields fall back to the current values.

    Returns
    -------
    DigitalTwinResult
        MUST NOT write to DB.
    """
    # ------------------------------------------------------------------
    # Build current snapshot
    # ------------------------------------------------------------------
    shipment_id      = str(current_scenario.get("shipment_id") or "")
    tracking_number  = str(current_scenario.get("tracking_number") or shipment_id)

    cur_route_id     = str(current_scenario.get("current_route_id") or "")
    cur_carrier_id   = str(current_scenario.get("current_carrier_id") or "")
    cur_hours        = float(current_scenario.get("estimated_hours") or 0.0)
    cur_cost         = float(current_scenario.get("total_cost_usd") or 0.0)
    cur_risk         = float(current_scenario.get("risk_score") or 0.0)
    cur_risk_level   = str(current_scenario.get("risk_level") or _risk_level_from_score(cur_risk))
    cur_on_time      = float(current_scenario.get("on_time_probability") or 0.5)

    current = ScenarioSnapshot(
        shipment_id=shipment_id,
        tracking_number=tracking_number,
        route_id=cur_route_id,
        carrier_id=cur_carrier_id,
        estimated_hours=cur_hours,
        total_cost_usd=cur_cost,
        risk_score=cur_risk,
        risk_level=cur_risk_level,
        on_time_probability=cur_on_time,
    )

    # ------------------------------------------------------------------
    # Build simulated snapshot — override only provided fields
    # ------------------------------------------------------------------
    sim_route_id   = str(simulated_changes.get("simulated_route_id")   or cur_route_id)
    sim_carrier_id = str(simulated_changes.get("simulated_carrier_id") or cur_carrier_id)
    sim_hours      = float(simulated_changes.get("simulated_estimated_hours")    or cur_hours)
    sim_cost       = float(simulated_changes.get("simulated_total_cost_usd")     or cur_cost)
    sim_risk       = float(simulated_changes.get("simulated_risk_score")         or cur_risk)
    sim_on_time    = float(simulated_changes.get("simulated_on_time_probability") or cur_on_time)
    sim_risk_level = _risk_level_from_score(sim_risk)

    simulated = ScenarioSnapshot(
        shipment_id=shipment_id,
        tracking_number=tracking_number,
        route_id=sim_route_id,
        carrier_id=sim_carrier_id,
        estimated_hours=sim_hours,
        total_cost_usd=sim_cost,
        risk_score=sim_risk,
        risk_level=sim_risk_level,
        on_time_probability=sim_on_time,
    )

    # ------------------------------------------------------------------
    # Compute deltas (simulated - current)
    # ------------------------------------------------------------------
    delta = ScenarioDelta(
        hours_delta=round(sim_hours - cur_hours, 2),
        cost_delta_usd=round(sim_cost - cur_cost, 2),
        risk_score_delta=round(sim_risk - cur_risk, 2),
        on_time_delta=round(sim_on_time - cur_on_time, 4),
        hours_change_pct=_safe_pct(sim_hours, cur_hours),
        cost_change_pct=_safe_pct(sim_cost, cur_cost),
        risk_change_pct=_safe_pct(sim_risk, cur_risk),
    )

    # ------------------------------------------------------------------
    # Recommendation: SWITCH if simulated is better on primary metrics
    # ------------------------------------------------------------------
    # Primary: risk must improve OR on_time must improve meaningfully
    risk_improves    = delta.risk_score_delta < -5.0
    on_time_improves = delta.on_time_delta > 0.05
    cost_acceptable  = delta.cost_delta_usd <= cur_cost * 0.20  # ≤ 20% cost increase
    eta_acceptable   = delta.hours_delta <= 4.0                  # ≤ 4h slower

    should_switch = (
        (risk_improves or on_time_improves)
        and cost_acceptable
        and eta_acceptable
    )
    recommendation = "SWITCH" if should_switch else "KEEP"

    confidence = _compute_confidence(delta, simulated)

    # ------------------------------------------------------------------
    # Factors
    # ------------------------------------------------------------------
    factors: List[str] = []
    factors.append(
        f"Digital Twin analysis for shipment {tracking_number} — "
        f"comparing current vs simulated scenario"
    )

    # ETA
    if delta.hours_delta < 0:
        factors.append(f"ETA improves: {abs(delta.hours_delta):.1f}h faster ({delta.hours_change_pct:.1f}%)")
    elif delta.hours_delta > 0:
        factors.append(f"ETA worsens: {delta.hours_delta:.1f}h slower ({delta.hours_change_pct:.1f}%)")
    else:
        factors.append("ETA unchanged")

    # Cost
    if delta.cost_delta_usd < 0:
        factors.append(f"Cost improves: ${abs(delta.cost_delta_usd):,.0f} savings ({delta.cost_change_pct:.1f}%)")
    elif delta.cost_delta_usd > 0:
        factors.append(f"Cost increases: +${delta.cost_delta_usd:,.0f} ({delta.cost_change_pct:.1f}%)")
    else:
        factors.append("Cost unchanged")

    # Risk
    if delta.risk_score_delta < 0:
        factors.append(
            f"Risk improves: {cur_risk_level} → {sim_risk_level} "
            f"(score {cur_risk:.1f} → {sim_risk:.1f}, {delta.risk_change_pct:.1f}%)"
        )
    elif delta.risk_score_delta > 0:
        factors.append(
            f"Risk worsens: {cur_risk_level} → {sim_risk_level} "
            f"(score {cur_risk:.1f} → {sim_risk:.1f}, +{delta.risk_change_pct:.1f}%)"
        )
    else:
        factors.append("Risk unchanged")

    # On-time
    if delta.on_time_delta > 0:
        factors.append(
            f"On-time probability improves: {cur_on_time:.0%} → {sim_on_time:.0%}"
        )
    elif delta.on_time_delta < 0:
        factors.append(
            f"On-time probability worsens: {cur_on_time:.0%} → {sim_on_time:.0%}"
        )

    factors.append(
        f"Recommendation: {recommendation} (confidence {confidence:.0%})"
    )

    return DigitalTwinResult(
        current=current,
        simulated=simulated,
        delta=delta,
        recommendation=recommendation,
        confidence=confidence,
        factors=factors,
    )
