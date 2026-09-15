"""
DisruptionImpactEngine — identifies shipments affected by a given disruption.

Pure Python — no FastAPI or SQLAlchemy imports.
Inputs: disruption dict, list of shipment dicts
Outputs: ImpactResult dataclass
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Any


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return great-circle distance in km using the existing Haversine formula."""
    earth_radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return earth_radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@dataclass
class ImpactedShipment:
    shipment_id: str
    impact_reason: str  # geo_intersection | route_blocked | both
    distance_to_epicenter_km: float | None = None
    impact_score: int = 0
    impact_level: str = "LOW"
    estimated_delay_hours: float = 0.0
    factors: list[str] = field(default_factory=list)


@dataclass
class ImpactResult:
    disruption_id: str
    affected_count: int
    impacted_shipments: list[ImpactedShipment] = field(default_factory=list)


_SEVERITY_SCORES = {"low": 15, "medium": 30, "high": 45, "critical": 60}
_BASE_DELAYS = {"low": 4.0, "medium": 12.0, "high": 24.0, "critical": 48.0}


def _duration_hours(disruption: dict[str, Any]) -> float:
    """Return the planned disruption duration, or zero when it is unavailable."""
    start = disruption.get("start_time")
    end = disruption.get("estimated_end_time")
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        return 0.0
    try:
        return max((end - start).total_seconds() / 3600, 0.0)
    except TypeError:
        # A mix of aware and naive datetimes is invalid input, not an engine error.
        return 0.0


def _impact_level(score: int) -> str:
    """Map a clamped score to LOW (0-24), MEDIUM (25-49), HIGH (50-74), or CRITICAL (75-100)."""
    if score <= 24:
        return "LOW"
    if score <= 49:
        return "MEDIUM"
    if score <= 74:
        return "HIGH"
    return "CRITICAL"


def _score_impact(
    disruption: dict[str, Any],
    shipment: dict[str, Any],
    impact_reason: str,
    distance_km: float | None,
) -> tuple[int, str, float, list[str]]:
    """Calculate deterministic score, level, delay, and raw-score factors for one match."""
    severity = str(disruption.get("severity") or "").lower()
    severity_score = _SEVERITY_SCORES.get(severity, 0)
    factors: list[str] = []
    raw_score = 0

    if severity_score:
        raw_score += severity_score
        factors.append(f"{severity.title()} severity disruption (+{severity_score})")

    exposure_score, multiplier, exposure_factor = {
        "geo_intersection": (10, 1.0, "Shipment intersects disruption area (+10)"),
        "route_blocked": (15, 1.5, "Shipment route is directly blocked (+15)"),
        "both": (20, 1.75, "Shipment intersects disruption area and route is directly blocked (+20)"),
    }[impact_reason]
    raw_score += exposure_score
    factors.append(exposure_factor)

    if distance_km is not None:
        if distance_km <= 50:
            raw_score += 10
            factors.append("Shipment is within 50 km of disruption (+10)")
        elif distance_km <= 150:
            raw_score += 5
            factors.append("Shipment is within 150 km of disruption (+5)")

    cargo_type = str(shipment.get("cargo_type") or "").lower()
    if cargo_type == "temperature_sensitive":
        raw_score += 5
        factors.append("Temperature-sensitive cargo (+5)")
    if cargo_type == "hazmat":
        raw_score += 5
        factors.append("Hazmat cargo (+5)")

    duration_hours = _duration_hours(disruption)
    if duration_hours > 48:
        raw_score += 5
        factors.append("Disruption expected to last more than 48 hours (+5)")
    if duration_hours > 96:
        raw_score += 5
        factors.append("Disruption expected to last more than 96 hours (+5)")

    if str(shipment.get("status") or "").lower() in {"at_risk", "delayed"}:
        raw_score += 5
        factors.append("Shipment is already at risk or delayed (+5)")

    # Factors deliberately retain raw contributions even if this cap applies.
    impact_score = min(raw_score, 100)
    base_delay = _BASE_DELAYS.get(severity, 0.0)
    duration_bonus = base_delay * 0.5 if duration_hours > 48 else 0.0
    estimated_delay_hours = round(base_delay * multiplier + duration_bonus, 1)
    return impact_score, _impact_level(impact_score), estimated_delay_hours, factors


def run(
    disruption: dict[str, Any],
    shipments: list[dict[str, Any]],
) -> ImpactResult:
    """
    Identify all shipments affected by *disruption*.

    A shipment is affected if:
      - Its current position is within the disruption's affected_radius_km, OR
      - Its route code appears in disruption.affected_route_codes

    Args:
        disruption: dict with keys:
            id, epicenter_lat, epicenter_lng, affected_radius_km,
            affected_route_codes (list[str]), severity
        shipments: list of dicts with keys:
            id, current_lat, current_lng, route_code (str | None)

    Returns:
        ImpactResult with all matching shipments.
    """
    disruption_id = str(disruption["id"])
    epicenter_lat = float(disruption["epicenter_lat"])
    epicenter_lng = float(disruption["epicenter_lng"])
    radius_km = float(disruption["affected_radius_km"])
    affected_route_codes: list[str] = [
        str(c) for c in (disruption.get("affected_route_codes") or [])
    ]

    impacted: list[ImpactedShipment] = []

    for shipment in shipments:
        shipment_id = str(shipment["id"])
        geo_match = False
        route_match = False
        distance_km: float | None = None

        # Geo-intersection check
        lat = shipment.get("current_lat")
        lng = shipment.get("current_lng")
        if lat is not None and lng is not None:
            try:
                distance_km = haversine(
                    float(lat), float(lng), epicenter_lat, epicenter_lng
                )
                geo_match = distance_km <= radius_km
            except (TypeError, ValueError):
                pass

        # Route code check
        route_code = shipment.get("route_code")
        if route_code and str(route_code) in affected_route_codes:
            route_match = True

        if geo_match or route_match:
            if geo_match and route_match:
                reason = "both"
            elif geo_match:
                reason = "geo_intersection"
            else:
                reason = "route_blocked"

            score, level, delay, factors = _score_impact(
                disruption, shipment, reason, distance_km
            )
            impacted.append(
                ImpactedShipment(
                    shipment_id=shipment_id,
                    impact_reason=reason,
                    distance_to_epicenter_km=round(distance_km, 2)
                    if distance_km is not None
                    else None,
                    impact_score=score,
                    impact_level=level,
                    estimated_delay_hours=delay,
                    factors=factors,
                )
            )

    return ImpactResult(
        disruption_id=disruption_id,
        affected_count=len(impacted),
        impacted_shipments=impacted,
    )
