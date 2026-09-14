"""Synthetic seed data for SupplyChainOS development and demonstration environments."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.carrier import Carrier
from backend.models.route import Route
from backend.models.fleet import Fleet
from backend.models.shipment import Shipment
from backend.models.disruption import Disruption
from backend.models.temperature_log import TemperatureLog

logger = logging.getLogger(__name__)

# ── City Coordinates ──────────────────────────────────────────────────────────
CITY_COORDS: dict[str, tuple[float, float]] = {
    "Frankfurt": (50.1109, 8.6821),
    "Hamburg": (53.5511, 9.9937),
    "Rotterdam": (51.9244, 4.4777),
    "Antwerp": (51.2194, 4.4025),
    "Berlin": (52.5200, 13.4050),
    "Munich": (48.1351, 11.5820),
    "Paris": (48.8566, 2.3522),
    "Milan": (45.4642, 9.1900),
    "London": (51.5074, -0.1278),
    "Amsterdam": (52.3676, 4.9041),
    "Shanghai": (31.2304, 121.4737),
    "Singapore": (1.3521, 103.8198),
    "Hong Kong": (22.3193, 114.1694),
    "Tokyo": (35.6762, 139.6503),
    "Dubai": (25.2048, 55.2708),
    "Mumbai": (19.0760, 72.8777),
    "Chicago": (41.8781, -87.6298),
    "New York": (40.7128, -74.0060),
    "Los Angeles": (34.0522, -118.2437),
    "Seattle": (47.6062, -122.3321),
    "Houston": (29.7604, -95.3698),
    "Atlanta": (33.7490, -84.3880),
    "Toronto": (43.6532, -79.3832),
    "Sydney": (33.8688, 151.2093),
    "Busan": (35.1796, 129.0756),
}

# ── Carriers (Exactly 10) ─────────────────────────────────────────────────────
CARRIER_DATA: list[dict[str, Any]] = [
    {
        "name": "Apex Global Freight",
        "code": "APEX",
        "type": "road",
        "reliability_score": 0.94,
        "cost_index": 1.10,
        "coverage_regions": ["Europe", "Central"],
        "contact_name": "Marcus Weber",
        "contact_email": "m.weber@apex-freight.com",
    },
    {
        "name": "TransEuropa Express",
        "code": "TEX",
        "type": "rail",
        "reliability_score": 0.91,
        "cost_index": 0.95,
        "coverage_regions": ["Europe"],
        "contact_name": "Elena Rostova",
        "contact_email": "operations@transeuropa.eu",
    },
    {
        "name": "Nordic Marine Lines",
        "code": "NML",
        "type": "sea",
        "reliability_score": 0.88,
        "cost_index": 0.75,
        "coverage_regions": ["North Sea", "Baltic", "Atlantic"],
        "contact_name": "Lars Lindholm",
        "contact_email": "charter@nordicmarine.com",
    },
    {
        "name": "AeroWings Cargo",
        "code": "AWC",
        "type": "air",
        "reliability_score": 0.97,
        "cost_index": 1.65,
        "coverage_regions": ["Global", "Europe", "Asia", "North America"],
        "contact_name": "Sarah Jenkins",
        "contact_email": "dispatch@aerowings.com",
    },
    {
        "name": "Continental MultiModal",
        "code": "CMM",
        "type": "multimodal",
        "reliability_score": 0.89,
        "cost_index": 1.05,
        "coverage_regions": ["Europe", "Central Asia"],
        "contact_name": "Antoine Dupont",
        "contact_email": "info@continental-mm.com",
    },
    {
        "name": "Pacific Star Shipping",
        "code": "PSS",
        "type": "sea",
        "reliability_score": 0.86,
        "cost_index": 0.70,
        "coverage_regions": ["Asia-Pacific", "Trans-Pacific"],
        "contact_name": "Wei Zhang",
        "contact_email": "pacific@starshipping.cn",
    },
    {
        "name": "Rhine-Alpine Railways",
        "code": "RAR",
        "type": "rail",
        "reliability_score": 0.93,
        "cost_index": 0.90,
        "coverage_regions": ["Rhine Corridor", "Central Europe"],
        "contact_name": "Hans Becker",
        "contact_email": "h.becker@rar-cargo.de",
    },
    {
        "name": "Vanguard Roadways",
        "code": "VGR",
        "type": "road",
        "reliability_score": 0.87,
        "cost_index": 1.00,
        "coverage_regions": ["Western Europe", "UK"],
        "contact_name": "David Miller",
        "contact_email": "ops@vanguard-road.co.uk",
    },
    {
        "name": "Orient Express Logistics",
        "code": "OEL",
        "type": "multimodal",
        "reliability_score": 0.85,
        "cost_index": 0.98,
        "coverage_regions": ["Asia", "Middle East"],
        "contact_name": "Priya Sharma",
        "contact_email": "contact@orientexpress.in",
    },
    {
        "name": "SkyFreight International",
        "code": "SFI",
        "type": "air",
        "reliability_score": 0.96,
        "cost_index": 1.70,
        "coverage_regions": ["Global", "North America", "Europe"],
        "contact_name": "Robert Taylor",
        "contact_email": "air@skyfreight-intl.com",
    },
]

# ── Routes (Exactly 30) ───────────────────────────────────────────────────────
ROUTE_DATA: list[dict[str, Any]] = [
    {"code": "RT-01", "name": "Hamburg to Frankfurt Road Express", "origin": "Hamburg", "destination": "Frankfurt", "mode": "road", "distance_km": 492.0, "typical_duration_hours": 6.5, "cost_per_kg_usd": 0.45, "reliability_score": 0.92, "waypoints": []},
    {"code": "RT-02", "name": "Rotterdam to Munich Rail Link", "origin": "Rotterdam", "destination": "Munich", "mode": "rail", "distance_km": 820.0, "typical_duration_hours": 14.0, "cost_per_kg_usd": 0.35, "reliability_score": 0.90, "waypoints": []},
    {"code": "RT-03", "name": "Antwerp to Paris Highway Corridor", "origin": "Antwerp", "destination": "Paris", "mode": "road", "distance_km": 345.0, "typical_duration_hours": 4.5, "cost_per_kg_usd": 0.40, "reliability_score": 0.94, "waypoints": []},
    {"code": "RT-04", "name": "Frankfurt to Milan Trans-Alpine Road", "origin": "Frankfurt", "destination": "Milan", "mode": "road", "distance_km": 668.0, "typical_duration_hours": 8.5, "cost_per_kg_usd": 0.55, "reliability_score": 0.89, "waypoints": []},
    {"code": "RT-05", "name": "London to Amsterdam Air Shuttle", "origin": "London", "destination": "Amsterdam", "mode": "air", "distance_km": 360.0, "typical_duration_hours": 2.5, "cost_per_kg_usd": 1.80, "reliability_score": 0.96, "waypoints": []},
    {"code": "RT-06", "name": "Rotterdam to Hamburg Coastal Sea", "origin": "Rotterdam", "destination": "Hamburg", "mode": "sea", "distance_km": 480.0, "typical_duration_hours": 24.0, "cost_per_kg_usd": 0.15, "reliability_score": 0.86, "waypoints": []},
    {"code": "RT-07", "name": "Berlin to Munich InterCity Rail", "origin": "Berlin", "destination": "Munich", "mode": "rail", "distance_km": 585.0, "typical_duration_hours": 7.0, "cost_per_kg_usd": 0.32, "reliability_score": 0.93, "waypoints": []},
    {"code": "RT-08", "name": "Paris to London EuroTunnel Road", "origin": "Paris", "destination": "London", "mode": "road", "distance_km": 460.0, "typical_duration_hours": 7.5, "cost_per_kg_usd": 0.60, "reliability_score": 0.88, "waypoints": []},
    {"code": "RT-09", "name": "Frankfurt to Berlin Autobahn", "origin": "Frankfurt", "destination": "Berlin", "mode": "road", "distance_km": 550.0, "typical_duration_hours": 6.0, "cost_per_kg_usd": 0.42, "reliability_score": 0.91, "waypoints": []},
    {"code": "RT-10", "name": "Amsterdam to Antwerp Inland Barge", "origin": "Amsterdam", "destination": "Antwerp", "mode": "multimodal", "distance_km": 160.0, "typical_duration_hours": 6.0, "cost_per_kg_usd": 0.22, "reliability_score": 0.92, "waypoints": []},
    {"code": "RT-11", "name": "Shanghai to Singapore Maritime Trunk", "origin": "Shanghai", "destination": "Singapore", "mode": "sea", "distance_km": 4200.0, "typical_duration_hours": 120.0, "cost_per_kg_usd": 0.18, "reliability_score": 0.87, "waypoints": []},
    {"code": "RT-12", "name": "Hong Kong to Tokyo Air Express", "origin": "Hong Kong", "destination": "Tokyo", "mode": "air", "distance_km": 2900.0, "typical_duration_hours": 4.5, "cost_per_kg_usd": 2.20, "reliability_score": 0.97, "waypoints": []},
    {"code": "RT-13", "name": "Dubai to Mumbai Maritime Channel", "origin": "Dubai", "destination": "Mumbai", "mode": "sea", "distance_km": 1930.0, "typical_duration_hours": 60.0, "cost_per_kg_usd": 0.25, "reliability_score": 0.89, "waypoints": []},
    {"code": "RT-14", "name": "Singapore to Hong Kong Sea Route", "origin": "Singapore", "destination": "Hong Kong", "mode": "sea", "distance_km": 2600.0, "typical_duration_hours": 72.0, "cost_per_kg_usd": 0.20, "reliability_score": 0.90, "waypoints": []},
    {"code": "RT-15", "name": "Shanghai to Busan Feedership", "origin": "Shanghai", "destination": "Busan", "mode": "sea", "distance_km": 850.0, "typical_duration_hours": 28.0, "cost_per_kg_usd": 0.22, "reliability_score": 0.91, "waypoints": []},
    {"code": "RT-16", "name": "Chicago to New York Rail Freight", "origin": "Chicago", "destination": "New York", "mode": "rail", "distance_km": 1300.0, "typical_duration_hours": 28.0, "cost_per_kg_usd": 0.38, "reliability_score": 0.89, "waypoints": []},
    {"code": "RT-17", "name": "Los Angeles to Seattle I-5 Highway", "origin": "Los Angeles", "destination": "Seattle", "mode": "road", "distance_km": 1820.0, "typical_duration_hours": 22.0, "cost_per_kg_usd": 0.52, "reliability_score": 0.90, "waypoints": []},
    {"code": "RT-18", "name": "Houston to Atlanta Interstate 10-85", "origin": "Houston", "destination": "Atlanta", "mode": "road", "distance_km": 1270.0, "typical_duration_hours": 16.0, "cost_per_kg_usd": 0.48, "reliability_score": 0.93, "waypoints": []},
    {"code": "RT-19", "name": "New York to London Transatlantic Air", "origin": "New York", "destination": "London", "mode": "air", "distance_km": 5570.0, "typical_duration_hours": 7.0, "cost_per_kg_usd": 3.40, "reliability_score": 0.95, "waypoints": []},
    {"code": "RT-20", "name": "Chicago to Houston Midwest-Gulf Rail", "origin": "Chicago", "destination": "Houston", "mode": "rail", "distance_km": 1740.0, "typical_duration_hours": 36.0, "cost_per_kg_usd": 0.36, "reliability_score": 0.88, "waypoints": []},
    {"code": "RT-21", "name": "Toronto to Chicago Cross-Border Road", "origin": "Toronto", "destination": "Chicago", "mode": "road", "distance_km": 830.0, "typical_duration_hours": 10.0, "cost_per_kg_usd": 0.50, "reliability_score": 0.91, "waypoints": []},
    {"code": "RT-22", "name": "Tokyo to Sydney Oceanic Route", "origin": "Tokyo", "destination": "Sydney", "mode": "sea", "distance_km": 7800.0, "typical_duration_hours": 210.0, "cost_per_kg_usd": 0.28, "reliability_score": 0.85, "waypoints": []},
    {"code": "RT-23", "name": "Mumbai to Frankfurt Air Cargo", "origin": "Mumbai", "destination": "Frankfurt", "mode": "air", "distance_km": 6560.0, "typical_duration_hours": 9.0, "cost_per_kg_usd": 3.80, "reliability_score": 0.94, "waypoints": []},
    {"code": "RT-24", "name": "Milan to Paris Alpine Freight Rail", "origin": "Milan", "destination": "Paris", "mode": "rail", "distance_km": 850.0, "typical_duration_hours": 12.0, "cost_per_kg_usd": 0.44, "reliability_score": 0.87, "waypoints": []},
    {"code": "RT-25", "name": "Rotterdam to Antwerp Pipeline & Barge", "origin": "Rotterdam", "destination": "Antwerp", "mode": "multimodal", "distance_km": 100.0, "typical_duration_hours": 4.0, "cost_per_kg_usd": 0.20, "reliability_score": 0.96, "waypoints": []},
    {"code": "RT-26", "name": "Hamburg to Berlin Northern Rail", "origin": "Hamburg", "destination": "Berlin", "mode": "rail", "distance_km": 290.0, "typical_duration_hours": 3.5, "cost_per_kg_usd": 0.28, "reliability_score": 0.94, "waypoints": []},
    {"code": "RT-27", "name": "Seattle to Chicago Northern Transcon Rail", "origin": "Seattle", "destination": "Chicago", "mode": "rail", "distance_km": 3400.0, "typical_duration_hours": 64.0, "cost_per_kg_usd": 0.42, "reliability_score": 0.86, "waypoints": []},
    {"code": "RT-28", "name": "Dubai to Singapore Air Super-Highway", "origin": "Dubai", "destination": "Singapore", "mode": "air", "distance_km": 5850.0, "typical_duration_hours": 7.5, "cost_per_kg_usd": 3.10, "reliability_score": 0.96, "waypoints": []},
    {"code": "RT-29", "name": "Los Angeles to Houston Southern Highway", "origin": "Los Angeles", "destination": "Houston", "mode": "road", "distance_km": 2480.0, "typical_duration_hours": 28.0, "cost_per_kg_usd": 0.54, "reliability_score": 0.90, "waypoints": []},
    {"code": "RT-30", "name": "Busan to Tokyo Coastal Ferry & Rail", "origin": "Busan", "destination": "Tokyo", "mode": "multimodal", "distance_km": 1150.0, "typical_duration_hours": 30.0, "cost_per_kg_usd": 0.65, "reliability_score": 0.92, "waypoints": []},
]


async def run_seed(session: AsyncSession) -> None:
    """Idempotently seed reference carriers, routes, fleet, and demo shipments."""
    # Check if carriers already exist
    existing = await session.execute(select(Carrier.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        logger.info("Database already contains carrier data; skipping seed.")
        return

    logger.info("Seeding reference data: carriers, routes, fleet, disruptions...")
    now = datetime.now(timezone.utc)

    # 1. Carriers
    carrier_entities: list[Carrier] = []
    for cd in CARRIER_DATA:
        c = Carrier(
            id=uuid.uuid4(),
            name=cd["name"],
            code=cd["code"],
            type=cd["type"],
            reliability_score=cd["reliability_score"],
            cost_index=cd["cost_index"],
            coverage_regions=cd["coverage_regions"],
            contact_name=cd.get("contact_name"),
            contact_email=cd.get("contact_email"),
            active=True,
            created_at=now,
        )
        session.add(c)
        carrier_entities.append(c)

    await session.flush()

    # 2. Routes
    route_entities: list[Route] = []
    for rd in ROUTE_DATA:
        r = Route(
            id=uuid.uuid4(),
            name=rd["name"],
            code=rd["code"],
            origin=rd["origin"],
            destination=rd["destination"],
            mode=rd["mode"],
            distance_km=rd["distance_km"],
            typical_duration_hours=rd["typical_duration_hours"],
            cost_per_kg_usd=rd["cost_per_kg_usd"],
            reliability_score=rd["reliability_score"],
            waypoints=rd.get("waypoints") or [],
            active=True,
            created_at=now,
        )
        session.add(r)
        route_entities.append(r)

    await session.flush()

    # 3. Fleet Assets
    fleet_entities: list[Fleet] = []
    fleet_configs = [
        ("FL-TRK-101", "truck", 24.0, 18.0, False, "in_transit", 53.2, 9.8),
        ("FL-TRK-102", "reefer_truck", 20.0, 15.0, True, "in_transit", 50.8, 8.2),
        ("FL-TRK-103", "reefer_truck", 20.0, 2.0, True, "available", 50.11, 8.68),
        ("FL-TRK-104", "truck", 24.0, 3.0, False, "available", 53.55, 9.99),
        ("FL-VAN-201", "van", 3.5, 0.5, True, "idle", 51.92, 4.47),
        ("FL-TRK-105", "truck", 26.0, 25.5, False, "in_transit", 48.85, 2.35),
    ]
    for code, v_type, cap, load, reefer, status, lat, lng in fleet_configs:
        f = Fleet(
            id=uuid.uuid4(),
            vehicle_code=code,
            vehicle_type=v_type,
            capacity_tons=cap,
            current_load_tons=load,
            is_refrigerated=reefer,
            status=status,
            latitude=lat,
            longitude=lng,
            created_at=now,
            updated_at=now,
        )
        session.add(f)
        fleet_entities.append(f)

    await session.flush()

    # 4. Disruptions
    disruptions_data = [
        ("North Sea Winter Gale", "severe_weather", "critical", 54.0, 9.5, 250.0, "active", 14.0),
        ("Frankfurt Rail Hub Signal Failure", "infrastructure", "high", 50.11, 8.68, 60.0, "active", 8.0),
        ("Shanghai Port Typhoon Diversion", "cyclone", "high", 31.23, 121.47, 180.0, "active", 24.0),
        ("Chicago Yard Winter Freezing", "severe_weather", "medium", 41.88, -87.63, 120.0, "active", 6.0),
        ("Malacca Strait Traffic Congestion", "port_congestion", "medium", 1.35, 103.82, 80.0, "active", 10.0),
    ]
    disruption_entities: list[Disruption] = []
    for title, d_type, sev, lat, lng, rad, stat, delay in disruptions_data:
        d = Disruption(
            id=uuid.uuid4(),
            title=title,
            type=d_type,
            severity=sev,
            latitude=lat,
            longitude=lng,
            affected_radius_km=rad,
            status=stat,
            description=f"Automated alert: {title}",
            estimated_delay_hours=delay,
            reported_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(d)
        disruption_entities.append(d)

    await session.flush()

    # 5. Shipments
    shipment_1 = Shipment(
        id=uuid.uuid4(),
        tracking_number="TRK-PHARMA-2026-001",
        origin="Hamburg",
        destination="Frankfurt",
        origin_lat=53.5511,
        origin_lng=9.9937,
        destination_lat=50.1109,
        destination_lng=8.6821,
        current_location="Kassel Junction",
        current_lat=51.3127,
        current_lng=9.4797,
        carrier_id=carrier_entities[0].id,
        route_id=route_entities[0].id,
        fleet_id=fleet_entities[1].id,
        status="at_risk",
        scheduled_departure=now - timedelta(hours=4),
        scheduled_arrival=now + timedelta(hours=3),
        estimated_arrival=now + timedelta(hours=7),
        cargo_type="temperature_sensitive",
        cargo_value_usd=185000.0,
        weight_kg=4200.0,
        temperature_required=True,
        temp_min_c=2.0,
        temp_max_c=8.0,
        risk_score=78.5,
        risk_level="high",
        ml_risk_score=75.0,
        combined_risk_score=77.0,
        created_at=now,
        updated_at=now,
    )
    session.add(shipment_1)
    await session.flush()

    # Temperature log for shipment 1
    t_log = TemperatureLog(
        id=uuid.uuid4(),
        shipment_id=shipment_1.id,
        recorded_at=now - timedelta(minutes=15),
        temperature_c=8.9,
        humidity_percent=62.0,
        is_excursion=True,
        ambient_temp_c=24.0,
    )
    session.add(t_log)

    logger.info("Seed data creation completed successfully.")
