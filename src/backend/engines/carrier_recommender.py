"""
CarrierRecommendationEngine — Phase 2D

Ranks available carriers for a shipment based on:
    - Historical on-time delivery rate
    - Current available capacity vs required capacity
    - Spot / contract cost efficiency
    - Reefer capability match for temperature-sensitive cargo
    - Active shipment load (busyness penalty)

Input contract
--------------
No ORM / DB access inside this file.
The router fetches and passes plain dicts.

carriers : list of dicts
    Each dict must have:
        id                  str | UUID
        name                str
        carrier_code        str
        on_time_rate        float   0.0–1.0   historical on-time delivery rate
        available_capacity  float   tonnes currently unallocated
        spot_rate_usd_per_km float  current spot cost per km
        active_shipments    int     number of shipments currently in transit
        max_shipments       int     operational capacity ceiling
        has_reefer          bool    whether refrigerated capacity is available
        reliability_score   float   0.0–1.0   composite reliability

shipment_context : dict | None
    required_capacity   float   minimum tonnes needed
    route_distance_km   float   planned route distance
    requires_reefer     bool    temperature-sensitive cargo
    shipment_priority   str     "low" | "medium" | "high" | "critical"

Output
------
CarrierRecommendationResult dataclass:
    ranked_carriers     list[RankedCarrier]  sorted best → worst
    recommended_carrier RankedCarrier | None
    factors             list[str]

Scoring formula (weighted sum → 0–100):
    On-time rate     35%
    Spot cost        30%
    Available capacity 25%
    Busyness         10%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

WEIGHT_ON_TIME   = 0.35
WEIGHT_COST      = 0.30
WEIGHT_CAPACITY  = 0.25
WEIGHT_BUSYNESS  = 0.10

# Priority → reliability minimum threshold
_PRIORITY_MIN_RELIABILITY: Dict[str, float] = {
    "low":      0.0,
    "medium":   0.70,
    "high":     0.80,
    "critical": 0.90,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RankedCarrier:
    id: str
    name: str
    carrier_code: str
    on_time_rate: float
    available_capacity: float
    spot_rate_usd_per_km: float
    estimated_cost_usd: float
    active_shipments: int
    max_shipments: int
    has_reefer: bool
    reliability_score: float
    on_time_score: float          # 0–100
    cost_score: float             # 0–100
    capacity_score: float         # 0–100
    busyness_score: float         # 0–100
    composite_score: float        # 0–100
    reefer_eligible: bool         # meets reefer requirement
    meets_priority_threshold: bool
    rank: int
    recommendation_reason: str


@dataclass
class CarrierRecommendationResult:
    ranked_carriers: List[RankedCarrier]
    recommended_carrier: Optional[RankedCarrier]
    factors: List[str]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def recommend_carriers(
    carriers: List[Dict[str, Any]],
    shipment_context: Optional[Dict[str, Any]] = None,
) -> CarrierRecommendationResult:
    """
    Rank carriers for a shipment by reliability, cost, and capacity.

    Parameters
    ----------
    carriers : list of dicts
        Carrier records from DB.
    shipment_context : dict | None
        Shipment requirements for scoring adjustments.

    Returns
    -------
    CarrierRecommendationResult
    """
    ctx = shipment_context or {}
    required_capacity = float(ctx.get("required_capacity") or 1.0)
    route_distance_km = float(ctx.get("route_distance_km") or 100.0)
    requires_reefer   = bool(ctx.get("requires_reefer") or False)
    priority          = str(ctx.get("shipment_priority") or "medium").lower()
    min_reliability   = _PRIORITY_MIN_RELIABILITY.get(priority, 0.0)
    factors: List[str] = []

    if not carriers:
        return CarrierRecommendationResult(
            ranked_carriers=[],
            recommended_carrier=None,
            factors=["No carriers provided for evaluation"],
        )

    # ------------------------------------------------------------------
    # Normalisation ranges
    # ------------------------------------------------------------------
    all_rates       = [float(c.get("spot_rate_usd_per_km") or 1.0) for c in carriers]
    all_on_time     = [float(c.get("on_time_rate") or 0.0)          for c in carriers]
    all_capacities  = [float(c.get("available_capacity") or 0.0)    for c in carriers]

    min_rate, max_rate = min(all_rates), max(all_rates)
    rate_range = max(max_rate - min_rate, 0.01)

    # ------------------------------------------------------------------
    # Score each carrier
    # ------------------------------------------------------------------
    scored: List[RankedCarrier] = []

    for c in carriers:
        cid             = str(c.get("id") or "")
        name            = str(c.get("name") or cid)
        code            = str(c.get("carrier_code") or "")
        on_time         = float(c.get("on_time_rate") or 0.0)
        avail_cap       = float(c.get("available_capacity") or 0.0)
        spot_rate       = float(c.get("spot_rate_usd_per_km") or 1.0)
        active          = int(c.get("active_shipments") or 0)
        max_ships       = int(c.get("max_shipments") or 1)
        has_reefer      = bool(c.get("has_reefer") or False)
        reliability     = float(c.get("reliability_score") or on_time)

        estimated_cost  = round(spot_rate * route_distance_km, 2)

        # --- On-time score (0–100) ---
        on_time_score = round(on_time * 100.0, 2)

        # --- Cost score (0–100, lower rate = higher score) ---
        cost_score = round(100.0 - ((spot_rate - min_rate) / rate_range) * 100.0, 2)

        # --- Capacity score (0–100) ---
        if avail_cap >= required_capacity:
            capacity_score = 100.0
        elif avail_cap > 0:
            capacity_score = round((avail_cap / required_capacity) * 100.0, 2)
        else:
            capacity_score = 0.0

        # --- Busyness score (0–100, lower active/max ratio = better) ---
        busy_ratio = active / max(max_ships, 1)
        busyness_score = round((1.0 - min(busy_ratio, 1.0)) * 100.0, 2)

        # --- Composite ---
        composite = round(
            WEIGHT_ON_TIME  * on_time_score
            + WEIGHT_COST   * cost_score
            + WEIGHT_CAPACITY * capacity_score
            + WEIGHT_BUSYNESS * busyness_score,
            2,
        )

        # Eligibility flags
        reefer_eligible = (not requires_reefer) or has_reefer
        meets_threshold = reliability >= min_reliability and avail_cap >= required_capacity

        # Penalty: heavily penalise carriers that fail eligibility
        if not reefer_eligible:
            composite = max(composite - 40.0, 0.0)
        if avail_cap < required_capacity:
            composite = max(composite - 25.0, 0.0)

        # Recommendation reason
        if not reefer_eligible:
            reason = "No refrigerated capacity — ineligible for temperature-sensitive cargo"
        elif avail_cap < required_capacity:
            reason = f"Insufficient capacity: {avail_cap:.1f}t available, {required_capacity:.1f}t required"
        elif on_time >= 0.90 and cost_score >= 60:
            reason = f"Premium carrier — {on_time*100:.0f}% on-time, cost-competitive"
        elif on_time >= 0.80:
            reason = f"Reliable carrier — {on_time*100:.0f}% on-time rate"
        else:
            reason = f"Budget option — lower on-time rate ({on_time*100:.0f}%)"

        scored.append(RankedCarrier(
            id=cid, name=name, carrier_code=code,
            on_time_rate=on_time, available_capacity=avail_cap,
            spot_rate_usd_per_km=spot_rate, estimated_cost_usd=estimated_cost,
            active_shipments=active, max_shipments=max_ships,
            has_reefer=has_reefer, reliability_score=reliability,
            on_time_score=on_time_score, cost_score=cost_score,
            capacity_score=capacity_score, busyness_score=busyness_score,
            composite_score=composite,
            reefer_eligible=reefer_eligible, meets_priority_threshold=meets_threshold,
            rank=0, recommendation_reason=reason,
        ))

    # ------------------------------------------------------------------
    # Sort: ineligible last, then by composite desc
    # ------------------------------------------------------------------
    scored.sort(key=lambda x: (
        not x.reefer_eligible,
        x.available_capacity < required_capacity,
        -x.composite_score,
    ))
    for i, carrier in enumerate(scored):
        carrier.rank = i + 1

    # Recommended = top eligible carrier
    eligible = [c for c in scored if c.reefer_eligible and c.available_capacity >= required_capacity]
    recommended = eligible[0] if eligible else (scored[0] if scored else None)

    # ------------------------------------------------------------------
    # Factors
    # ------------------------------------------------------------------
    factors.append(f"Evaluated {len(scored)} carrier(s) for {priority.upper()} priority shipment")
    factors.append(
        f"Scoring weights — On-time: {WEIGHT_ON_TIME:.0%}, "
        f"Cost: {WEIGHT_COST:.0%}, Capacity: {WEIGHT_CAPACITY:.0%}, "
        f"Busyness: {WEIGHT_BUSYNESS:.0%}"
    )
    factors.append(f"Required capacity: {required_capacity:.1f}t | Route distance: {route_distance_km:.0f} km")
    if requires_reefer:
        factors.append("Reefer requirement active — non-refrigerated carriers penalised")
    if min_reliability > 0:
        factors.append(f"Priority {priority.upper()} threshold: minimum {min_reliability*100:.0f}% reliability")

    ineligible_count = sum(1 for c in scored if not c.reefer_eligible)
    if ineligible_count:
        factors.append(f"{ineligible_count} carrier(s) ineligible — no reefer capability")

    if recommended:
        factors.append(
            f"Recommended: '{recommended.name}' "
            f"(score {recommended.composite_score}, "
            f"on-time {recommended.on_time_rate*100:.0f}%, "
            f"est. cost ${recommended.estimated_cost_usd:,.0f})"
        )

    return CarrierRecommendationResult(
        ranked_carriers=scored,
        recommended_carrier=recommended,
        factors=factors,
    )
