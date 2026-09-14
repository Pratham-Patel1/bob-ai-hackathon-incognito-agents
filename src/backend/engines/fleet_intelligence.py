"""
FleetIntelligenceEngine — Phase 2C

Analyses fleet asset status and identifies:
  - Idle vehicles       (utilisation < 20%)
  - Available vehicles  (in depot / available status)
  - Overloaded vehicles (utilisation > 95%)
  - Best candidates for redeployment (proximity + reefer match + capacity)

Input contract
--------------
No ORM / DB access inside this file.
The router passes a list of fleet vehicle dicts and an optional request context.

fleet_vehicles : list of dicts
    Each dict must have (matching Fleet model fields):
        id                  str | UUID
        vehicle_code        str
        vehicle_type        str     e.g. "truck", "reefer_truck", "van"
        capacity_tons       float
        current_load_tons   float
        is_refrigerated     bool
        status              str     "available" | "idle" | "in_transit" | "maintenance"
        latitude            float
        longitude           float

request_context : dict | None
    Optional keys used for candidate matching:
        epicenter_lat       float   disruption/origin latitude
        epicenter_lng       float   disruption/origin longitude
        required_capacity   float   minimum tons needed
        requires_reefer     bool    whether refrigerated unit is needed

Output
------
FleetIntelligenceResult dataclass:
    idle_vehicles           list[FleetVehicleSummary]
    available_vehicles      list[FleetVehicleSummary]
    overloaded_vehicles     list[FleetVehicleSummary]
    redeployment_candidates list[FleetVehicleSummary]  sorted by suitability score
    summary                 FleetSummaryStats
    factors                 list[str]
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Utilisation thresholds
# ---------------------------------------------------------------------------

IDLE_UTILISATION_THRESHOLD = 0.20        # < 20%  → idle
OVERLOADED_UTILISATION_THRESHOLD = 0.95  # > 95%  → overloaded

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FleetVehicleSummary:
    id: str
    vehicle_code: str
    vehicle_type: str
    capacity_tons: float
    current_load_tons: float
    utilisation_percent: float
    is_refrigerated: bool
    status: str
    latitude: float
    longitude: float
    distance_km: Optional[float]          # from epicenter if provided
    suitability_score: float              # 0–100 for candidate ranking


@dataclass
class FleetSummaryStats:
    total_vehicles: int
    idle_count: int
    available_count: int
    overloaded_count: int
    in_transit_count: int
    maintenance_count: int
    average_utilisation_percent: float
    refrigerated_available: int


@dataclass
class FleetIntelligenceResult:
    idle_vehicles: List[FleetVehicleSummary]
    available_vehicles: List[FleetVehicleSummary]
    overloaded_vehicles: List[FleetVehicleSummary]
    redeployment_candidates: List[FleetVehicleSummary]
    summary: FleetSummaryStats
    factors: List[str]


# ---------------------------------------------------------------------------
# Geo helper
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres."""
    R = 6_371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Suitability scoring
# ---------------------------------------------------------------------------

def _suitability_score(
    vehicle: FleetVehicleSummary,
    required_capacity: float,
    requires_reefer: bool,
    max_distance_km: float,
) -> float:
    """
    Score a vehicle's suitability for redeployment on a 0–100 scale.

    Factors:
        Proximity   (40 pts) — closer is better
        Capacity    (30 pts) — meets or exceeds required capacity
        Reefer      (20 pts) — matches refrigerated requirement
        Utilisation (10 pts) — lower utilisation preferred
    """
    score = 0.0

    # Proximity (40 pts)
    if vehicle.distance_km is not None:
        proximity_ratio = 1.0 - min(vehicle.distance_km / max(max_distance_km, 1), 1.0)
        score += proximity_ratio * 40.0

    # Capacity (30 pts)
    spare_capacity = vehicle.capacity_tons - vehicle.current_load_tons
    if spare_capacity >= required_capacity:
        score += 30.0
    elif spare_capacity > 0:
        score += (spare_capacity / required_capacity) * 30.0

    # Reefer match (20 pts)
    if requires_reefer:
        if vehicle.is_refrigerated:
            score += 20.0
    else:
        score += 20.0  # any vehicle is fine

    # Low utilisation (10 pts)
    score += (1.0 - vehicle.utilisation_percent / 100.0) * 10.0

    return round(min(score, 100.0), 2)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def analyse_fleet(
    fleet_vehicles: List[Dict[str, Any]],
    request_context: Optional[Dict[str, Any]] = None,
) -> FleetIntelligenceResult:
    """
    Analyse fleet assets and produce intelligence report.

    Parameters
    ----------
    fleet_vehicles : list of dicts
        Vehicle records from the database (plain dicts, no ORM).
    request_context : dict | None
        Optional context for candidate matching (epicenter, capacity, reefer).

    Returns
    -------
    FleetIntelligenceResult
    """
    ctx = request_context or {}
    epicenter_lat: Optional[float] = ctx.get("epicenter_lat")
    epicenter_lng: Optional[float] = ctx.get("epicenter_lng")
    required_capacity: float = float(ctx.get("required_capacity") or 1.0)
    requires_reefer: bool = bool(ctx.get("requires_reefer") or False)

    idle_vehicles: List[FleetVehicleSummary] = []
    available_vehicles: List[FleetVehicleSummary] = []
    overloaded_vehicles: List[FleetVehicleSummary] = []
    all_summaries: List[FleetVehicleSummary] = []

    total_utilisation = 0.0
    in_transit_count = 0
    maintenance_count = 0
    refrigerated_available = 0

    has_epicenter = epicenter_lat is not None and epicenter_lng is not None

    # Maximum distance seen (used for proximity normalisation)
    distances: List[float] = []

    for v in fleet_vehicles:
        cap = float(v.get("capacity_tons") or 1.0)
        load = float(v.get("current_load_tons") or 0.0)
        util = (load / cap * 100.0) if cap > 0 else 0.0

        lat = float(v.get("latitude") or 0.0)
        lng = float(v.get("longitude") or 0.0)

        dist_km: Optional[float] = None
        if has_epicenter:
            dist_km = round(_haversine_km(epicenter_lat, epicenter_lng, lat, lng), 1)
            distances.append(dist_km)

        summary = FleetVehicleSummary(
            id=str(v.get("id") or ""),
            vehicle_code=str(v.get("vehicle_code") or ""),
            vehicle_type=str(v.get("vehicle_type") or "truck"),
            capacity_tons=cap,
            current_load_tons=load,
            utilisation_percent=round(util, 1),
            is_refrigerated=bool(v.get("is_refrigerated") or False),
            status=str(v.get("status") or "unknown"),
            latitude=lat,
            longitude=lng,
            distance_km=dist_km,
            suitability_score=0.0,
        )
        all_summaries.append(summary)
        total_utilisation += util

        status = summary.status.lower()

        if status in ("available", "idle"):
            if util < IDLE_UTILISATION_THRESHOLD * 100:
                idle_vehicles.append(summary)
            else:
                available_vehicles.append(summary)

            if summary.is_refrigerated:
                refrigerated_available += 1

        elif status == "in_transit":
            in_transit_count += 1

        elif status == "maintenance":
            maintenance_count += 1

        if util > OVERLOADED_UTILISATION_THRESHOLD * 100:
            overloaded_vehicles.append(summary)

    # ------------------------------------------------------------------
    # Compute suitability scores for idle + available vehicles
    # ------------------------------------------------------------------
    max_dist = max(distances) if distances else 1000.0
    candidate_pool = idle_vehicles + [
        v for v in available_vehicles
        if v not in idle_vehicles
    ]

    for v in candidate_pool:
        v.suitability_score = _suitability_score(v, required_capacity, requires_reefer, max_dist)

    redeployment_candidates = sorted(candidate_pool, key=lambda v: v.suitability_score, reverse=True)

    # ------------------------------------------------------------------
    # Summary stats
    # ------------------------------------------------------------------
    n = len(all_summaries)
    avg_util = round(total_utilisation / n, 1) if n > 0 else 0.0

    summary_stats = FleetSummaryStats(
        total_vehicles=n,
        idle_count=len(idle_vehicles),
        available_count=len(available_vehicles),
        overloaded_count=len(overloaded_vehicles),
        in_transit_count=in_transit_count,
        maintenance_count=maintenance_count,
        average_utilisation_percent=avg_util,
        refrigerated_available=refrigerated_available,
    )

    # ------------------------------------------------------------------
    # Factors
    # ------------------------------------------------------------------
    factors: List[str] = []
    factors.append(f"Fleet analysed: {n} total vehicles")
    factors.append(
        f"Idle (<{int(IDLE_UTILISATION_THRESHOLD*100)}%): {len(idle_vehicles)} | "
        f"Available: {len(available_vehicles)} | "
        f"Overloaded (>{int(OVERLOADED_UTILISATION_THRESHOLD*100)}%): {len(overloaded_vehicles)}"
    )
    factors.append(f"Fleet average utilisation: {avg_util}%")
    factors.append(f"Refrigerated units available: {refrigerated_available}")

    if redeployment_candidates:
        best = redeployment_candidates[0]
        factors.append(
            f"Top redeployment candidate: {best.vehicle_code} "
            f"(score {best.suitability_score}, "
            f"{'reefer, ' if best.is_refrigerated else ''}"
            f"{best.capacity_tons - best.current_load_tons:.1f}t spare capacity"
            + (f", {best.distance_km:.0f} km from epicenter)" if best.distance_km else ")")
        )
    else:
        factors.append("No redeployment candidates found matching the request criteria")

    return FleetIntelligenceResult(
        idle_vehicles=idle_vehicles,
        available_vehicles=available_vehicles,
        overloaded_vehicles=overloaded_vehicles,
        redeployment_candidates=redeployment_candidates,
        summary=summary_stats,
        factors=factors,
    )
