"""
ORM Serializers — convert SQLAlchemy model instances to plain dictionaries for engine consumption.
Pure function engines require primitive dictionaries and ISO timestamps.
"""
from __future__ import annotations

from typing import Any
from datetime import datetime


def _to_iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def shipment_to_dict(shipment: Any) -> dict[str, Any]:
    """Convert a Shipment ORM model instance to engine dict format."""
    if not shipment:
        return {}
    if isinstance(shipment, dict):
        return shipment

    return {
        "id": str(shipment.id),
        "shipment_id": str(shipment.id),
        "tracking_number": shipment.tracking_number,
        "origin": shipment.origin,
        "destination": shipment.destination,
        "origin_lat": _to_float(shipment.origin_lat),
        "origin_lng": _to_float(shipment.origin_lng),
        "destination_lat": _to_float(shipment.destination_lat),
        "destination_lng": _to_float(shipment.destination_lng),
        "current_location": shipment.current_location,
        "current_lat": _to_float(shipment.current_lat),
        "current_lng": _to_float(shipment.current_lng),
        "carrier_id": str(shipment.carrier_id) if shipment.carrier_id else None,
        "route_id": str(shipment.route_id) if shipment.route_id else None,
        "fleet_id": str(shipment.fleet_id) if shipment.fleet_id else None,
        "status": shipment.status,
        "scheduled_departure": _to_iso(shipment.scheduled_departure),
        "scheduled_arrival": _to_iso(shipment.scheduled_arrival),
        "estimated_arrival": _to_iso(shipment.estimated_arrival),
        "actual_arrival": _to_iso(shipment.actual_arrival),
        "cargo_type": shipment.cargo_type,
        "cargo_value_usd": _to_float(shipment.cargo_value_usd) or 0.0,
        "weight_kg": _to_float(shipment.weight_kg) or 0.0,
        "temperature_required": bool(shipment.temperature_required),
        "temp_min_c": _to_float(shipment.temp_min_c),
        "temp_max_c": _to_float(shipment.temp_max_c),
        "risk_score": _to_float(shipment.risk_score) or 0.0,
        "risk_level": shipment.risk_level,
        "ml_risk_score": _to_float(shipment.ml_risk_score),
        "combined_risk_score": _to_float(shipment.combined_risk_score),
        "created_at": _to_iso(getattr(shipment, "created_at", None)),
        "updated_at": _to_iso(getattr(shipment, "updated_at", None)),
    }


def disruption_to_dict(disruption: Any) -> dict[str, Any]:
    """Convert a Disruption ORM model instance to engine dict format."""
    if not disruption:
        return {}
    if isinstance(disruption, dict):
        return disruption

    d_type = getattr(disruption, "type", getattr(disruption, "category", "weather"))
    starts = _to_iso(getattr(disruption, "start_time", getattr(disruption, "starts_at", None)))
    ends = _to_iso(getattr(disruption, "estimated_end_time", getattr(disruption, "expected_end", None)))
    resolved = _to_iso(getattr(disruption, "actual_end_time", getattr(disruption, "resolved_at", None)))

    return {
        "id": str(disruption.id),
        "disruption_id": str(disruption.id),
        "code": getattr(disruption, "code", f"DISR-{str(disruption.id)[:8]}"),
        "title": disruption.title,
        "description": disruption.description,
        "category": d_type,
        "type": d_type,
        "severity": disruption.severity,
        "status": disruption.status,
        "epicenter_lat": _to_float(disruption.epicenter_lat),
        "epicenter_lng": _to_float(disruption.epicenter_lng),
        "lat": _to_float(disruption.epicenter_lat),
        "lng": _to_float(disruption.epicenter_lng),
        "affected_radius_km": _to_float(disruption.affected_radius_km) or 100.0,
        "affected_route_codes": getattr(disruption, "affected_route_codes", []),
        "starts_at": starts,
        "start_time": starts,
        "expected_end": ends,
        "estimated_end_time": ends,
        "resolved_at": resolved,
        "impact_delay_hours": _to_float(getattr(disruption, "impact_delay_hours", None)) or 0.0,
    }


def fleet_to_dict(fleet: Any) -> dict[str, Any]:
    """Convert a Fleet ORM model instance to engine dict format."""
    if not fleet:
        return {}
    if isinstance(fleet, dict):
        return fleet

    # capacity_kg converted to capacity_tons for engines
    cap_kg = _to_float(getattr(fleet, "capacity_kg", None))
    cap_tons = (cap_kg / 1000.0) if cap_kg else (_to_float(getattr(fleet, "capacity_tons", None)) or 10.0)

    load_kg = _to_float(getattr(fleet, "current_load_kg", None))
    load_tons = (load_kg / 1000.0) if load_kg else (_to_float(getattr(fleet, "current_load_tons", None)) or 0.0)

    is_reefer = bool(getattr(fleet, "temperature_capable", getattr(fleet, "is_refrigerated", False)))

    return {
        "id": str(fleet.id),
        "fleet_id": str(fleet.id),
        "vehicle_id": fleet.vehicle_id,
        "vehicle_type": getattr(fleet, "type", getattr(fleet, "vehicle_type", "truck")),
        "license_plate": getattr(fleet, "license_plate", fleet.vehicle_id),
        "make_model": getattr(fleet, "make_model", "Truck"),
        "capacity_tons": cap_tons,
        "capacity_kg": cap_kg or (cap_tons * 1000.0),
        "current_load_tons": load_tons,
        "current_load_kg": load_kg or (load_tons * 1000.0),
        "utilization_pct": _to_float(getattr(fleet, "utilization_pct", None)) or 0.0,
        "status": fleet.status,
        "current_lat": _to_float(fleet.current_lat),
        "current_lng": _to_float(fleet.current_lng),
        "current_location": fleet.current_location,
        "speed_kmh": _to_float(getattr(fleet, "speed_kmh", 0.0)) or 0.0,
        "heading_deg": _to_float(getattr(fleet, "heading_deg", 0.0)) or 0.0,
        "fuel_pct": _to_float(getattr(fleet, "fuel_pct", 100.0)) or 100.0,
        "is_refrigerated": is_reefer,
        "temperature_capable": is_reefer,
        "max_range_km": _to_float(getattr(fleet, "max_range_km", 1000.0)) or 1000.0,
        "driver_name": getattr(fleet, "driver_name", "Driver"),
        "driver_phone": getattr(fleet, "driver_phone", ""),
    }


def route_to_dict(route: Any) -> dict[str, Any]:
    """Convert a Route ORM model instance to engine dict format."""
    if not route:
        return {}
    if isinstance(route, dict):
        return route

    est_hours = _to_float(getattr(route, "typical_duration_hours", getattr(route, "estimated_hours", 0.0))) or 8.0
    cost = _to_float(getattr(route, "cost_per_kg_usd", 0.0)) or 2.50
    dist = _to_float(route.distance_km) or 500.0

    return {
        "id": str(route.id),
        "route_id": str(route.id),
        "code": route.code,
        "name": route.name,
        "origin": route.origin,
        "destination": route.destination,
        "origin_lat": _to_float(getattr(route, "origin_lat", None)),
        "origin_lng": _to_float(getattr(route, "origin_lng", None)),
        "destination_lat": _to_float(getattr(route, "destination_lat", None)),
        "destination_lng": _to_float(getattr(route, "destination_lng", None)),
        "distance_km": dist,
        "estimated_hours": est_hours,
        "typical_duration_hours": est_hours,
        "cost_per_kg_usd": cost,
        "total_cost_usd": cost * 1000.0,
        "risk_level": getattr(route, "risk_level", "low"),
        "toll_cost_usd": _to_float(getattr(route, "toll_cost_usd", 50.0)) or 50.0,
        "fuel_cost_usd": _to_float(getattr(route, "fuel_cost_usd", 150.0)) or 150.0,
        "reliability_score": _to_float(getattr(route, "reliability_score", 0.95)) or 0.95,
        "is_blocked": bool(getattr(route, "is_blocked", False)),
        "disruption_overlap": _to_float(getattr(route, "disruption_overlap", 0.0)) or 0.0,
        "mode": getattr(route, "mode", "road"),
        "waypoints": getattr(route, "waypoints", []) or [],
        "is_active": bool(getattr(route, "active", getattr(route, "is_active", True))),
    }


def carrier_to_dict(carrier: Any) -> dict[str, Any]:
    """Convert a Carrier ORM model instance to engine dict format."""
    if not carrier:
        return {}
    if isinstance(carrier, dict):
        return carrier

    rel_score = _to_float(getattr(carrier, "reliability_score", getattr(carrier, "on_time_delivery_rate", 0.90))) or 0.90
    cost_idx = _to_float(getattr(carrier, "cost_index", getattr(carrier, "cost_per_km_usd", 2.50))) or 2.50

    return {
        "id": str(carrier.id),
        "carrier_id": str(carrier.id),
        "name": carrier.name,
        "code": carrier.code,
        "contact_name": carrier.contact_name,
        "contact_email": carrier.contact_email,
        "contact_phone": getattr(carrier, "contact_phone", None),
        "rating": _to_float(getattr(carrier, "rating", 4.5)) or 4.5,
        "reliability_score": rel_score,
        "on_time_delivery_rate": rel_score,
        "on_time_rate": rel_score,
        "average_delay_hours": _to_float(getattr(carrier, "average_delay_hours", 0.0)) or 0.0,
        "safety_score": _to_float(getattr(carrier, "safety_score", 0.95)) or 0.95,
        "cost_index": cost_idx,
        "cost_per_km_usd": cost_idx,
        "is_preferred": bool(getattr(carrier, "is_preferred", False)),
        "is_active": bool(getattr(carrier, "active", getattr(carrier, "is_active", True))),
        "coverage_regions": getattr(carrier, "coverage_regions", []),
    }


def temperature_log_to_dict(log: Any) -> dict[str, Any]:
    """Convert a TemperatureLog ORM model instance to engine dict format."""
    if not log:
        return {}
    if isinstance(log, dict):
        return log

    return {
        "id": str(log.id),
        "shipment_id": str(log.shipment_id) if getattr(log, "shipment_id", None) else None,
        "recorded_at": _to_iso(getattr(log, "recorded_at", None)),
        "timestamp": _to_iso(getattr(log, "recorded_at", None)),
        "temperature_c": _to_float(getattr(log, "temperature_c", None)),
        "ambient_temp_c": _to_float(getattr(log, "ambient_temp_c", None)),
        "humidity_pct": _to_float(getattr(log, "humidity_pct", None)),
        "location": getattr(log, "location", None),
        "lat": _to_float(getattr(log, "lat", None)),
        "lng": _to_float(getattr(log, "lng", None)),
        "is_excursion": bool(getattr(log, "is_excursion", False)),
        "severity": getattr(log, "severity", getattr(log, "excursion_severity", "none")),
        "excursion_severity": getattr(log, "excursion_severity", "none"),
    }
