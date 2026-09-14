"""
RouteOptimizationEngine — Phase 2D

Evaluates and ranks alternative routes when a shipment's primary route
is blocked or at high risk due to a disruption.

Input contract
--------------
No ORM / DB access inside this file.
The router fetches data from DB and passes plain dicts.

routes : list of dicts
    Each dict must have:
        id                  str | UUID
        name                str
        origin              str
        destination         str
        distance_km         float
        estimated_hours     float    normal transit time
        risk_level          str      "low" | "medium" | "high" | "critical"
        toll_cost_usd       float
        fuel_cost_usd       float
        reliability_score   float    0.0–1.0  (historical on-time rate)
        is_blocked          bool     True if currently disruption-blocked
        disruption_overlap  float    0.0–1.0  fraction of route inside disruption zone

optimization_context : dict | None
    shipment_priority       str     "low" | "medium" | "high" | "critical"
    cargo_value_usd         float
    temperature_sensitive   bool
    deadline_hours          float   hours remaining until delivery deadline

Output
------
RouteOptimizationResult dataclass:
    ranked_routes       list[RankedRoute]  sorted best → worst
    recommended_route   RankedRoute        top pick
    factors             list[str]

Scoring formula (weighted sum → 0–100):
    Safety / disruption avoidance  40%
    ETA / delay minimisation       35%
    Cost efficiency                25%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

WEIGHT_SAFETY = 0.40
WEIGHT_ETA    = 0.35
WEIGHT_COST   = 0.25

# Risk level → safety penalty (subtracted from safety score)
_RISK_PENALTIES: Dict[str, float] = {
    "low":      0.0,
    "medium":  20.0,
    "high":    50.0,
    "critical":90.0,
}

# Priority → deadline urgency multiplier on ETA weight
_PRIORITY_ETA_MULTIPLIER: Dict[str, float] = {
    "low":      1.0,
    "medium":   1.2,
    "high":     1.5,
    "critical": 2.0,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RankedRoute:
    id: str
    name: str
    origin: str
    destination: str
    distance_km: float
    estimated_hours: float
    risk_level: str
    total_cost_usd: float
    reliability_score: float
    is_blocked: bool
    disruption_overlap: float
    safety_score: float          # 0–100
    eta_score: float             # 0–100
    cost_score: float            # 0–100
    composite_score: float       # 0–100
    rank: int
    recommendation_reason: str


@dataclass
class RouteOptimizationResult:
    ranked_routes: List[RankedRoute]
    recommended_route: Optional[RankedRoute]
    factors: List[str]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def optimize_routes(
    routes: List[Dict[str, Any]],
    optimization_context: Optional[Dict[str, Any]] = None,
) -> RouteOptimizationResult:
    """
    Rank candidate routes by safety, ETA, and cost.

    Parameters
    ----------
    routes : list of dicts
        Route records from DB — must include the fields in the module docstring.
    optimization_context : dict | None
        Shipment-level context for weighting adjustments.

    Returns
    -------
    RouteOptimizationResult
    """
    ctx = optimization_context or {}
    priority = str(ctx.get("shipment_priority") or "medium").lower()
    temperature_sensitive = bool(ctx.get("temperature_sensitive") or False)
    deadline_hours = float(ctx.get("deadline_hours") or 48.0)
    cargo_value_usd = float(ctx.get("cargo_value_usd") or 0.0)
    factors: List[str] = []

    if not routes:
        return RouteOptimizationResult(
            ranked_routes=[],
            recommended_route=None,
            factors=["No routes provided for optimisation"],
        )

    # ------------------------------------------------------------------
    # Derived weight adjustments
    # ------------------------------------------------------------------
    eta_multiplier = _PRIORITY_ETA_MULTIPLIER.get(priority, 1.0)
    # For urgent / high-value shipments, boost ETA weight proportionally
    adjusted_weight_eta = min(WEIGHT_ETA * eta_multiplier, 0.55)
    # Re-normalise so weights sum to 1.0
    leftover = 1.0 - adjusted_weight_eta
    ratio = WEIGHT_SAFETY / (WEIGHT_SAFETY + WEIGHT_COST)
    adjusted_weight_safety = leftover * ratio
    adjusted_weight_cost   = leftover * (1.0 - ratio)

    # ------------------------------------------------------------------
    # Extract min / max for normalisation
    # ------------------------------------------------------------------
    all_hours  = [float(r.get("estimated_hours") or 1) for r in routes]
    all_costs  = [float(r.get("toll_cost_usd") or 0) + float(r.get("fuel_cost_usd") or 0) for r in routes]

    min_hours, max_hours = min(all_hours), max(all_hours)
    min_cost,  max_cost  = min(all_costs),  max(all_costs)

    hour_range = max(max_hours - min_hours, 1.0)
    cost_range = max(max_cost  - min_cost,  1.0)

    # ------------------------------------------------------------------
    # Score each route
    # ------------------------------------------------------------------
    scored: List[RankedRoute] = []

    for r in routes:
        rid     = str(r.get("id") or "")
        name    = str(r.get("name") or rid)
        origin  = str(r.get("origin") or "")
        dest    = str(r.get("destination") or "")
        dist    = float(r.get("distance_km") or 0)
        hours   = float(r.get("estimated_hours") or 1)
        risk    = str(r.get("risk_level") or "low").lower()
        toll    = float(r.get("toll_cost_usd") or 0)
        fuel    = float(r.get("fuel_cost_usd") or 0)
        reliability = float(r.get("reliability_score") or 0.8)
        is_blocked  = bool(r.get("is_blocked") or False)
        overlap     = float(r.get("disruption_overlap") or 0.0)
        total_cost  = toll + fuel

        # --- Safety score (0–100) ---
        risk_penalty = _RISK_PENALTIES.get(risk, 0.0)
        overlap_penalty = overlap * 40.0          # 100% overlap → -40 pts
        # Reliability bonus (up to +8 pts) applied before cap
        reliability_bonus = (reliability - 0.5) * 16.0   # 0.5 → 0 pts, 1.0 → 8 pts
        safety_raw = 100.0 - risk_penalty - overlap_penalty + reliability_bonus
        # Blocked route overrides everything → safety = 0
        if is_blocked:
            safety_score = 0.0
        else:
            safety_score = round(max(min(safety_raw, 100.0), 0.0), 2)

        # --- ETA score (0–100, lower hours = higher score) ---
        eta_score = round(100.0 - ((hours - min_hours) / hour_range) * 100.0, 2)

        # --- Cost score (0–100, lower cost = higher score) ---
        cost_score = round(100.0 - ((total_cost - min_cost) / cost_range) * 100.0, 2)

        # --- Composite ---
        composite = round(
            adjusted_weight_safety * safety_score
            + adjusted_weight_eta   * eta_score
            + adjusted_weight_cost  * cost_score,
            2,
        )

        # Reason summary
        if is_blocked:
            reason = "Route currently blocked — not recommended"
        elif risk == "low" and overlap == 0.0:
            reason = "Safest corridor — no disruption overlap"
        elif safety_score >= 70:
            reason = f"Reliable alternative — {risk} risk, {hours:.0f}h ETA"
        else:
            reason = f"Suboptimal — {risk} risk, {overlap*100:.0f}% disruption overlap"

        scored.append(RankedRoute(
            id=rid, name=name, origin=origin, destination=dest,
            distance_km=dist, estimated_hours=hours, risk_level=risk,
            total_cost_usd=round(total_cost, 2), reliability_score=reliability,
            is_blocked=is_blocked, disruption_overlap=overlap,
            safety_score=safety_score, eta_score=eta_score, cost_score=cost_score,
            composite_score=composite, rank=0,
            recommendation_reason=reason,
        ))

    # ------------------------------------------------------------------
    # Sort: highest composite first; blocked routes always last
    # ------------------------------------------------------------------
    scored.sort(key=lambda x: (x.is_blocked, -x.composite_score))
    for i, route in enumerate(scored):
        route.rank = i + 1

    recommended = scored[0] if scored else None

    # ------------------------------------------------------------------
    # Factors
    # ------------------------------------------------------------------
    factors.append(f"Evaluated {len(scored)} route(s) for shipment priority: {priority.upper()}")
    factors.append(
        f"Scoring weights — Safety: {adjusted_weight_safety:.0%}, "
        f"ETA: {adjusted_weight_eta:.0%}, Cost: {adjusted_weight_cost:.0%}"
    )
    if temperature_sensitive:
        factors.append("Temperature-sensitive cargo — safety & ETA prioritised")
    if recommended:
        factors.append(
            f"Top route: '{recommended.name}' (score {recommended.composite_score}, "
            f"risk {recommended.risk_level.upper()}, "
            f"ETA {recommended.estimated_hours:.0f}h, "
            f"cost ${recommended.total_cost_usd:,.0f})"
        )
        blocked_count = sum(1 for r in scored if r.is_blocked)
        if blocked_count:
            factors.append(f"{blocked_count} route(s) excluded — currently blocked by disruption")

    return RouteOptimizationResult(
        ranked_routes=scored,
        recommended_route=recommended,
        factors=factors,
    )
