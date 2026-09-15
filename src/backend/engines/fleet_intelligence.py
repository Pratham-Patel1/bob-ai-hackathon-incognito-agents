"""
FleetIntelligenceEngine — idle/overloaded detection + redeployment suggestions.

Pure Python — no FastAPI or SQLAlchemy imports.
Uses haversine for nearest-vehicle matching.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.geo import haversine

IDLE_THRESHOLD_PCT = 20.0
OVERLOADED_THRESHOLD_PCT = 95.0


@dataclass
class FleetAnalysis:
    idle_count: int
    overloaded_count: int
    idle_vehicle_ids: list[str] = field(default_factory=list)
    overloaded_vehicle_ids: list[str] = field(default_factory=list)
    utilization_histogram: dict[str, int] = field(default_factory=dict)


@dataclass
class RedeploymentSuggestion:
    vehicle_id: str
    target_shipment_id: str
    distance_km: float
    reason: str


def analyse_fleet(fleet: list[dict[str, Any]]) -> FleetAnalysis:
    """
    Classify each vehicle as idle, overloaded, or normal.

    Args:
        fleet: list of fleet dicts with keys:
            id, status, utilization_pct, current_lat, current_lng

    Returns:
        FleetAnalysis with counts and ID lists.
    """
    idle_ids: list[str] = []
    overloaded_ids: list[str] = []
    histogram: dict[str, int] = {
        "0-20": 0,
        "20-50": 0,
        "50-80": 0,
        "80-95": 0,
        "95-100": 0,
    }

    for v in fleet:
        vid = str(v["id"])
        status = v.get("status", "active")
        pct = float(v.get("utilization_pct") or 0)

        if status == "active":
            if pct < IDLE_THRESHOLD_PCT:
                idle_ids.append(vid)
            elif pct > OVERLOADED_THRESHOLD_PCT:
                overloaded_ids.append(vid)

        # Histogram
        if pct < 20:
            histogram["0-20"] += 1
        elif pct < 50:
            histogram["20-50"] += 1
        elif pct < 80:
            histogram["50-80"] += 1
        elif pct < 95:
            histogram["80-95"] += 1
        else:
            histogram["95-100"] += 1

    return FleetAnalysis(
        idle_count=len(idle_ids),
        overloaded_count=len(overloaded_ids),
        idle_vehicle_ids=idle_ids,
        overloaded_vehicle_ids=overloaded_ids,
        utilization_histogram=histogram,
    )


def suggest_redeployments(
    fleet: list[dict[str, Any]],
    needy_shipments: list[dict[str, Any]],
) -> list[RedeploymentSuggestion]:
    """
    For each idle vehicle, find the nearest delayed or unassigned shipment
    that matches vehicle type and capacity constraints.

    Args:
        fleet: list of fleet dicts (same as analyse_fleet input)
        needy_shipments: shipments needing a vehicle — each dict with keys:
            id, current_lat, current_lng, weight_kg, cargo_type,
            temperature_required (bool), fleet_id (None if unassigned)

    Returns:
        List of RedeploymentSuggestion (at most one per idle vehicle).
    """
    idle_vehicles = [
        v for v in fleet
        if v.get("status") == "active"
        and float(v.get("utilization_pct") or 0) < IDLE_THRESHOLD_PCT
    ]

    suggestions: list[RedeploymentSuggestion] = []

    for vehicle in idle_vehicles:
        vid = str(vehicle["id"])
        v_lat = vehicle.get("current_lat")
        v_lng = vehicle.get("current_lng")
        if v_lat is None or v_lng is None:
            continue

        v_capacity = float(vehicle.get("capacity_kg") or 0)
        v_temp_capable = bool(vehicle.get("temperature_capable", False))
        v_type = vehicle.get("type", "")

        best_shipment: dict | None = None
        best_distance = float("inf")

        for s in needy_shipments:
            s_lat = s.get("current_lat")
            s_lng = s.get("current_lng")
            if s_lat is None or s_lng is None:
                continue

            # Capacity constraint
            s_weight = float(s.get("weight_kg") or 0)
            if s_weight > v_capacity:
                continue

            # Temperature constraint
            if s.get("temperature_required") and not v_temp_capable:
                continue

            try:
                dist = haversine(float(v_lat), float(v_lng), float(s_lat), float(s_lng))
            except (TypeError, ValueError):
                continue

            if dist < best_distance:
                best_distance = dist
                best_shipment = s

        if best_shipment is not None:
            cargo_type = best_shipment.get("cargo_type", "general")
            reason = (
                f"Idle vehicle {vehicle.get('vehicle_id', vid)} "
                f"({v_type}) redeployed to shipment "
                f"{best_shipment.get('tracking_number', best_shipment['id'])} "
                f"({cargo_type}, {best_shipment.get('weight_kg', 0):.0f} kg). "
                f"Distance: {best_distance:.0f} km. "
                f"Capacity utilization after: "
                f"{float(best_shipment.get('weight_kg', 0)) / v_capacity * 100:.0f}%."
            )
            suggestions.append(
                RedeploymentSuggestion(
                    vehicle_id=vid,
                    target_shipment_id=str(best_shipment["id"]),
                    distance_km=round(best_distance, 2),
                    reason=reason,
                )
            )

    return suggestions
