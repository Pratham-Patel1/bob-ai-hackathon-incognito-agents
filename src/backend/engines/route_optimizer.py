"""
RouteOptimizationEngine — rank alternative routes for a disrupted shipment.

Pure Python — no FastAPI or SQLAlchemy imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouteOption:
    route_id: str
    route_code: str
    route_name: str
    score: float
    estimated_duration_hours: float
    estimated_cost_usd: float
    avoids_all_disruptions: bool
    reason: str


def run(
    shipment: dict[str, Any],
    active_disruptions: list[dict[str, Any]],
    available_routes: list[dict[str, Any]],
    top_n: int = 3,
) -> list[RouteOption]:
    """
    Find and rank alternative routes for a disrupted shipment.

    Args:
        shipment: dict with keys:
            origin, destination, weight_kg (float),
            temperature_required (bool), route_id (str | None)
        active_disruptions: list of disruption dicts with affected_route_codes
        available_routes: all route dicts with keys:
            id, code, name, origin, destination, mode,
            distance_km, typical_duration_hours, cost_per_kg_usd,
            reliability_score, active (bool)
        top_n: number of top routes to return.

    Returns:
        List of RouteOption, sorted by score descending, max top_n items.
        Returns empty list if no alternatives found.
    """
    origin = (shipment.get("origin") or "").strip().lower()
    destination = (shipment.get("destination") or "").strip().lower()
    weight_kg = float(shipment.get("weight_kg") or 1000)
    temp_required = bool(shipment.get("temperature_required", False))
    current_route_id = str(shipment.get("route_id") or "")

    # Collect all blocked route codes from active disruptions
    blocked_codes: set[str] = set()
    for d in active_disruptions:
        for code in (d.get("affected_route_codes") or []):
            blocked_codes.add(str(code))

    options: list[RouteOption] = []

    for route in available_routes:
        if not route.get("active", True):
            continue

        # Skip the shipment's current route
        if str(route.get("id") or "") == current_route_id:
            continue

        # Origin/destination match (case-insensitive prefix)
        r_origin = (route.get("origin") or "").strip().lower()
        r_dest = (route.get("destination") or "").strip().lower()

        if not _location_matches(r_origin, origin):
            continue
        if not _location_matches(r_dest, destination):
            continue

        route_code = str(route.get("code") or "")
        avoids_all = route_code not in blocked_codes

        # Score calculation
        reliability = float(route.get("reliability_score") or 0.7)
        distance_km = float(route.get("distance_km") or 1000)
        cost_per_kg = float(route.get("cost_per_kg_usd") or 0.5)
        duration_hours = float(route.get("typical_duration_hours") or 48)

        # Normalise distance and cost against baseline values
        distance_penalty = min(1.0, distance_km / 5000.0) * 0.1
        cost_penalty = min(1.0, cost_per_kg / 2.0) * 0.1
        disruption_bonus = 0.2 if avoids_all else 0.0

        score = reliability - distance_penalty - cost_penalty + disruption_bonus
        score = max(0.0, min(1.5, score))  # allow > 1.0 due to bonus

        estimated_cost = weight_kg * cost_per_kg

        reason_parts = [
            f"Route {route_code} ({route.get('name', '')}) "
            f"reliability {reliability:.2f}"
        ]
        if avoids_all:
            reason_parts.append("avoids all active disruption zones")
        else:
            reason_parts.append("passes through disruption zone (use with caution)")
        if temp_required:
            reason_parts.append("temperature-capable")
        reason_parts.append(
            f"est. {duration_hours:.0f}h, ${estimated_cost:,.0f} total"
        )

        options.append(
            RouteOption(
                route_id=str(route["id"]),
                route_code=route_code,
                route_name=str(route.get("name") or ""),
                score=round(score, 4),
                estimated_duration_hours=round(duration_hours, 2),
                estimated_cost_usd=round(estimated_cost, 2),
                avoids_all_disruptions=avoids_all,
                reason=". ".join(reason_parts) + ".",
            )
        )

    # Sort: avoids_all first, then by score descending
    options.sort(key=lambda o: (-int(o.avoids_all_disruptions), -o.score))
    return options[:top_n]


def _location_matches(route_loc: str, shipment_loc: str) -> bool:
    """
    Flexible location matching: exact, prefix, or substring.
    Both inputs should be lowercase-stripped.
    """
    if not shipment_loc or not route_loc:
        return False
    return (
        route_loc == shipment_loc
        or route_loc.startswith(shipment_loc[:4])
        or shipment_loc.startswith(route_loc[:4])
        or shipment_loc in route_loc
        or route_loc in shipment_loc
    )
