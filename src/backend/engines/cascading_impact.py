"""
CascadingImpactEngine — Phase 2E

Performs Depth=1 graph traversal to identify downstream ripple effects
when a shipment or vehicle is disrupted.

When one shipment is delayed, it may:
  - Block a vehicle that was scheduled to carry another shipment
  - Delay a shipment waiting at the same depot/hub
  - Overload an alternative carrier or route

Architecture rule:
  - Depth = 1 only (immediate downstream, not recursive)
  - NO DB access inside this file — caller passes plain dicts
  - Pure in-memory computation

Input contract
--------------
affected_shipment : dict
    The primary disrupted shipment (Shipment model fields as dict).

all_shipments : list of dicts
    All other active shipments to check for cascade effects.

all_vehicles : list of dicts
    All fleet vehicles to check for vehicle conflicts.

disruption : dict | None
    The disruption causing the cascade. Keys:
        id, disruption_type, severity, affected_region, radius_km,
        latitude, longitude

Output
------
CascadeImpactResult dataclass:
    directly_affected_shipment_ids  list[str]
    potentially_delayed_shipments   list[CascadeShipmentImpact]
    vehicle_conflicts               list[CascadeVehicleConflict]
    cascade_depth                   int   always 1
    total_affected_count            int
    factors                         list[str]
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CASCADE_DEPTH = 1

# Same-hub detection threshold (km) — shipments within this radius
# of the affected shipment's location share a "hub"
SAME_HUB_RADIUS_KM = 50.0

# Vehicle conflict: vehicle is linked to the disrupted shipment's fleet_id
# OR is positioned within disruption radius
VEHICLE_PROXIMITY_RADIUS_KM = 100.0

# Risk escalation — how much cascade adds to a downstream shipment's risk score
CASCADE_RISK_ESCALATION = 15.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CascadeShipmentImpact:
    shipment_id: str
    tracking_number: str
    reason: str                       # why it's affected
    estimated_extra_delay_hours: float
    cascade_risk_escalation: float    # points added to risk score


@dataclass
class CascadeVehicleConflict:
    vehicle_id: str
    vehicle_code: str
    reason: str
    impact: str                       # "reassignment_needed" | "at_risk"


@dataclass
class CascadeImpactResult:
    directly_affected_shipment_ids: List[str]
    potentially_delayed_shipments: List[CascadeShipmentImpact]
    vehicle_conflicts: List[CascadeVehicleConflict]
    cascade_depth: int
    total_affected_count: int
    factors: List[str]


# ---------------------------------------------------------------------------
# Geo helper
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def compute_cascade_impact(
    affected_shipment: Dict[str, Any],
    all_shipments: List[Dict[str, Any]],
    all_vehicles: List[Dict[str, Any]],
    disruption: Optional[Dict[str, Any]] = None,
) -> CascadeImpactResult:
    """
    Identify Depth=1 cascade effects of a shipment disruption.

    Parameters
    ----------
    affected_shipment : dict
        The primary shipment being disrupted.
    all_shipments : list of dicts
        All other active shipments to scan for ripple effects.
    all_vehicles : list of dicts
        All fleet vehicles to scan for conflicts.
    disruption : dict | None
        The triggering disruption record.

    Returns
    -------
    CascadeImpactResult
    """
    primary_id = str(affected_shipment.get("id") or "")
    primary_route_id   = str(affected_shipment.get("route_id") or "")
    primary_fleet_id   = str(affected_shipment.get("fleet_id") or "")
    primary_carrier_id = str(affected_shipment.get("carrier_id") or "")
    primary_lat  = float(affected_shipment.get("current_lat") or
                         affected_shipment.get("origin_lat") or 0.0)
    primary_lng  = float(affected_shipment.get("current_lng") or
                         affected_shipment.get("origin_lng") or 0.0)

    disruption_lat = float((disruption or {}).get("latitude") or primary_lat)
    disruption_lng = float((disruption or {}).get("longitude") or primary_lng)
    disruption_radius = float((disruption or {}).get("radius_km") or SAME_HUB_RADIUS_KM)
    disruption_severity = str((disruption or {}).get("severity") or "medium").lower()

    # Delay estimate by severity
    _severity_delay: Dict[str, float] = {
        "low": 4.0, "medium": 8.0, "high": 16.0, "critical": 24.0
    }
    estimated_extra_delay = _severity_delay.get(disruption_severity, 8.0)

    directly_affected: List[str] = [primary_id]
    delayed_shipments: List[CascadeShipmentImpact] = []
    vehicle_conflicts: List[CascadeVehicleConflict] = []
    seen_ship_ids: set = {primary_id}
    seen_veh_ids: set = set()

    # ------------------------------------------------------------------
    # Scan all other shipments for cascade
    # ------------------------------------------------------------------
    for s in all_shipments:
        sid = str(s.get("id") or "")
        if sid in seen_ship_ids:
            continue
        if str(s.get("status") or "").lower() in ("delivered", "cancelled"):
            continue

        reason: Optional[str] = None

        # 1. Same route
        if str(s.get("route_id") or "") == primary_route_id and primary_route_id:
            reason = f"Shares blocked route (route_id={primary_route_id})"

        # 2. Same vehicle / fleet asset
        elif str(s.get("fleet_id") or "") == primary_fleet_id and primary_fleet_id:
            reason = f"Shares vehicle (fleet_id={primary_fleet_id})"

        # 3. Same carrier
        elif str(s.get("carrier_id") or "") == primary_carrier_id and primary_carrier_id:
            s_lat = float(s.get("current_lat") or s.get("origin_lat") or 0.0)
            s_lng = float(s.get("current_lng") or s.get("origin_lng") or 0.0)
            if _haversine_km(disruption_lat, disruption_lng, s_lat, s_lng) <= disruption_radius:
                reason = f"Same carrier within disruption radius {disruption_radius:.0f}km"

        # 4. Geographic proximity — within same hub radius
        else:
            s_lat = float(s.get("current_lat") or s.get("origin_lat") or 0.0)
            s_lng = float(s.get("current_lng") or s.get("origin_lng") or 0.0)
            dist = _haversine_km(primary_lat, primary_lng, s_lat, s_lng)
            if dist <= SAME_HUB_RADIUS_KM:
                reason = f"Within same hub ({dist:.1f}km of affected shipment)"

        if reason:
            seen_ship_ids.add(sid)
            delayed_shipments.append(CascadeShipmentImpact(
                shipment_id=sid,
                tracking_number=str(s.get("tracking_number") or sid),
                reason=reason,
                estimated_extra_delay_hours=estimated_extra_delay,
                cascade_risk_escalation=CASCADE_RISK_ESCALATION,
            ))

    # ------------------------------------------------------------------
    # Scan vehicles for conflicts
    # ------------------------------------------------------------------
    for v in all_vehicles:
        vid = str(v.get("id") or "")
        if vid in seen_veh_ids:
            continue

        v_status = str(v.get("status") or "").lower()
        if v_status == "maintenance":
            continue

        conflict_reason: Optional[str] = None
        impact: str = "at_risk"

        # 1. Vehicle directly assigned to the disrupted shipment
        if vid == primary_fleet_id and primary_fleet_id:
            conflict_reason = "Vehicle assigned to disrupted shipment — needs reassignment"
            impact = "reassignment_needed"

        # 2. Vehicle within disruption zone
        else:
            v_lat = float(v.get("latitude") or 0.0)
            v_lng = float(v.get("longitude") or 0.0)
            dist = _haversine_km(disruption_lat, disruption_lng, v_lat, v_lng)
            if dist <= VEHICLE_PROXIMITY_RADIUS_KM:
                conflict_reason = (
                    f"Vehicle within disruption zone ({dist:.1f}km of epicenter, "
                    f"radius={disruption_radius:.0f}km)"
                )
                impact = "reassignment_needed" if dist <= disruption_radius else "at_risk"

        if conflict_reason:
            seen_veh_ids.add(vid)
            vehicle_conflicts.append(CascadeVehicleConflict(
                vehicle_id=vid,
                vehicle_code=str(v.get("vehicle_code") or vid),
                reason=conflict_reason,
                impact=impact,
            ))

    # ------------------------------------------------------------------
    # Build result
    # ------------------------------------------------------------------
    total = len(delayed_shipments) + len(vehicle_conflicts)
    factors: List[str] = []
    factors.append(
        f"Cascade analysis — Depth {CASCADE_DEPTH} | "
        f"Primary shipment: {affected_shipment.get('tracking_number', primary_id)}"
    )
    factors.append(f"Scanned {len(all_shipments)} shipments, {len(all_vehicles)} vehicles")
    if delayed_shipments:
        factors.append(
            f"{len(delayed_shipments)} downstream shipment(s) potentially delayed "
            f"(+{estimated_extra_delay:.0f}h each)"
        )
    else:
        factors.append("No downstream shipment cascades detected at Depth 1")
    if vehicle_conflicts:
        reassign = sum(1 for v in vehicle_conflicts if v.impact == "reassignment_needed")
        factors.append(
            f"{len(vehicle_conflicts)} vehicle conflict(s): "
            f"{reassign} need reassignment"
        )
    else:
        factors.append("No vehicle conflicts detected")

    return CascadeImpactResult(
        directly_affected_shipment_ids=directly_affected,
        potentially_delayed_shipments=delayed_shipments,
        vehicle_conflicts=vehicle_conflicts,
        cascade_depth=CASCADE_DEPTH,
        total_affected_count=total,
        factors=factors,
    )
