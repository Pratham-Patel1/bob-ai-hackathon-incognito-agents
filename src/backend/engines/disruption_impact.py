"""
DisruptionImpactEngine — Phase 2A-1.
Evaluates which shipments are affected by a disruption, calculates impact score,
impact level, estimated delay hours, and explainable contributing factors.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from backend.utils.geo import haversine

logger = logging.getLogger(__name__)


class DisruptionImpactEngine:
    """Evaluates disruption exposure, proximity, and multi-factor impact on shipments."""

    SEVERITY_SCORES: dict[str, int] = {
        "LOW": 15,
        "MEDIUM": 30,
        "HIGH": 45,
        "CRITICAL": 60,
    }

    BASE_DELAYS: dict[str, float] = {
        "LOW": 4.0,
        "MEDIUM": 12.0,
        "HIGH": 24.0,
        "CRITICAL": 48.0,
    }

    @staticmethod
    def _parse_iso(dt_val: Any) -> datetime | None:
        if not dt_val:
            return None
        if isinstance(dt_val, datetime):
            return dt_val
        try:
            return datetime.fromisoformat(str(dt_val).replace("Z", "+00:00"))
        except Exception:
            return None

    def evaluate_shipment(
        self,
        disruption: dict[str, Any],
        shipment: dict[str, Any],
        route: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate impact of a single disruption on a single shipment.

        Returns:
            dict containing:
                - shipment_id
                - is_affected
                - impact_score (0-100)
                - impact_level (LOW, MEDIUM, HIGH, CRITICAL)
                - estimated_delay_hours
                - distance_km
                - factors: list[str]
        """
        factors: list[str] = []
        severity = str(disruption.get("severity", "MEDIUM")).upper()
        sev_score = self.SEVERITY_SCORES.get(severity, 30)
        factors.append(f"{severity.capitalize()} severity disruption (+{sev_score})")

        # Disruption coordinates
        d_lat = disruption.get("epicenter_lat") or disruption.get("lat")
        d_lng = disruption.get("epicenter_lng") or disruption.get("lng")
        radius_km = float(disruption.get("affected_radius_km") or 100.0)

        # Shipment coordinates
        s_lat = shipment.get("current_lat") or shipment.get("origin_lat")
        s_lng = shipment.get("current_lng") or shipment.get("origin_lng")

        distance_km: float | None = None
        geo_intersected = False
        if d_lat is not None and d_lng is not None and s_lat is not None and s_lng is not None:
            distance_km = haversine(float(s_lat), float(s_lng), float(d_lat), float(d_lng))
            if distance_km <= radius_km:
                geo_intersected = True

        # Route blockage check
        route_blocked = False
        route_code = (route.get("code") if route else None) or shipment.get("route_code")
        disr_code = disruption.get("code", "")
        affected_routes = disruption.get("affected_route_codes") or []

        if route_code and (route_code in affected_routes or route_code in disr_code):
            route_blocked = True
        elif route and route.get("waypoints") and d_lat is not None and d_lng is not None:
            for wp in route.get("waypoints", []):
                if isinstance(wp, dict) and "lat" in wp and "lng" in wp:
                    wp_dist = haversine(float(wp["lat"]), float(wp["lng"]), float(d_lat), float(d_lng))
                    if wp_dist <= radius_km:
                        route_blocked = True
                        break

        # Exposure score & factor
        if geo_intersected and route_blocked:
            exp_score = 20
            factors.append("Shipment intersects disruption area and route is directly blocked (+20)")
        elif route_blocked:
            exp_score = 15
            factors.append("Shipment route is directly blocked (+15)")
        elif geo_intersected:
            exp_score = 10
            factors.append("Shipment is within disruption geographic radius (+10)")
        else:
            exp_score = 0

        # Proximity score & factor
        prox_score = 0
        if distance_km is not None:
            if distance_km <= 50.0:
                prox_score = 10
                factors.append(f"Immediate proximity to epicenter ({distance_km:.1f} km <= 50 km) (+10)")
            elif distance_km <= 150.0:
                prox_score = 5
                factors.append(f"Close proximity to epicenter ({distance_km:.1f} km <= 150 km) (+5)")

        # Cargo factors
        cargo_score = 0
        is_temp = (
            shipment.get("temperature_required")
            or shipment.get("cargo_type") == "temperature_sensitive"
        )
        if is_temp:
            cargo_score += 5
            factors.append("Temperature-sensitive cargo (+5)")

        if shipment.get("cargo_type") == "hazmat":
            cargo_score += 5
            factors.append("Hazmat cargo (+5)")

        # Duration factor
        duration_score = 0
        dur_hours = float(disruption.get("impact_delay_hours") or 0.0)
        s_time = self._parse_iso(disruption.get("starts_at"))
        e_time = self._parse_iso(disruption.get("expected_end"))
        if s_time and e_time:
            computed_dur = (e_time - s_time).total_seconds() / 3600.0
            dur_hours = max(dur_hours, computed_dur)

        if dur_hours > 96.0:
            duration_score = 10
            factors.append(f"Extended disruption duration ({dur_hours:.1f}h > 96h) (+10)")
        elif dur_hours > 48.0:
            duration_score = 5
            factors.append(f"Prolonged disruption duration ({dur_hours:.1f}h > 48h) (+5)")

        # Shipment status factor
        status_score = 0
        s_status = str(shipment.get("status", "")).lower()
        if s_status in ("delayed", "at_risk", "held"):
            status_score = 5
            factors.append(f"Shipment is already {s_status} (+5)")

        raw_score = sev_score + exp_score + prox_score + cargo_score + duration_score + status_score
        final_score = min(raw_score, 100)

        # Impact level
        if final_score < 25:
            impact_level = "LOW"
        elif final_score < 50:
            impact_level = "MEDIUM"
        elif final_score < 75:
            impact_level = "HIGH"
        else:
            impact_level = "CRITICAL"

        # Estimated delay calculation
        base_delay = self.BASE_DELAYS.get(severity, 12.0)
        if geo_intersected and route_blocked:
            multiplier = 1.75
        elif route_blocked:
            multiplier = 1.5
        elif geo_intersected:
            multiplier = 1.0
        else:
            multiplier = 0.5

        dur_bonus = (base_delay * 0.5) if dur_hours > 48.0 else 0.0
        estimated_delay = round(base_delay * multiplier + dur_bonus, 1)

        is_affected = geo_intersected or route_blocked or (distance_km is not None and distance_km <= radius_km)

        return {
            "shipment_id": shipment.get("id") or shipment.get("shipment_id"),
            "tracking_number": shipment.get("tracking_number"),
            "is_affected": is_affected,
            "impact_score": final_score,
            "raw_score": raw_score,
            "impact_level": impact_level,
            "estimated_delay_hours": estimated_delay,
            "distance_km": round(distance_km, 1) if distance_km is not None else None,
            "exposure": {
                "geo_intersected": geo_intersected,
                "route_blocked": route_blocked,
            },
            "factors": factors,
        }

    def evaluate_disruption(
        self,
        disruption: dict[str, Any],
        shipments: list[dict[str, Any]],
        routes_map: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate disruption impact across all provided shipments.

        Returns:
            dict containing:
                - disruption_id
                - total_shipments_evaluated
                - affected_shipments_count
                - high_or_critical_count
                - affected_shipments: list of evaluated shipments sorted by impact_score desc
        """
        routes_map = routes_map or {}
        evaluated: list[dict[str, Any]] = []

        for s in shipments:
            r_id = str(s.get("route_id", ""))
            route = routes_map.get(r_id)
            ev = self.evaluate_shipment(disruption, s, route=route)
            evaluated.append(ev)

        # Filter affected
        affected = [e for e in evaluated if e["is_affected"]]
        affected.sort(key=lambda x: x["impact_score"], reverse=True)

        high_or_crit = sum(1 for e in affected if e["impact_level"] in ("HIGH", "CRITICAL"))

        return {
            "disruption_id": disruption.get("id") or disruption.get("disruption_id"),
            "disruption_code": disruption.get("code"),
            "severity": disruption.get("severity"),
            "total_shipments_evaluated": len(shipments),
            "affected_shipments_count": len(affected),
            "high_or_critical_count": high_or_crit,
            "affected_shipments": affected,
        }
