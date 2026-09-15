"""
Placeholder routers — full engine integration in Phase 2/3.
Provides list endpoints so seed data is immediately queryable.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.models.shipment import Shipment
from backend.models.disruption import Disruption
from backend.models.fleet import Fleet
from backend.models.recommendation import Recommendation
from backend.models.decision_audit import DecisionAudit
from backend.models.carrier import Carrier
from backend.models.route import Route
from backend.schemas.shipment import ShipmentRead
from backend.schemas.disruption import DisruptionRead
from backend.schemas.fleet import FleetRead
from backend.schemas.recommendation import RecommendationRead
from backend.schemas.audit import AuditRead
from backend.schemas.carrier import CarrierRead
from backend.schemas.route import RouteRead

logger = logging.getLogger(__name__)

# ── Shipments ─────────────────────────────────────────────────────────────────
shipments_router = APIRouter(prefix="/shipments", tags=["shipments"])


@shipments_router.get("", response_model=list[ShipmentRead])
async def list_shipments(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(select(Shipment).order_by(Shipment.created_at.desc()))
    return result.scalars().all()


@shipments_router.get("/{shipment_id}", response_model=ShipmentRead)
async def get_shipment(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    from fastapi import HTTPException
    import uuid
    result = await session.execute(
        select(Shipment).where(Shipment.id == uuid.UUID(shipment_id))
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


# ── Disruptions ───────────────────────────────────────────────────────────────
disruptions_router = APIRouter(prefix="/disruptions", tags=["disruptions"])


@disruptions_router.get("", response_model=list[DisruptionRead])
async def list_disruptions(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(
        select(Disruption).where(Disruption.status != "resolved").order_by(Disruption.created_at.desc())
    )
    return result.scalars().all()


@disruptions_router.get("/{disruption_id}", response_model=DisruptionRead)
async def get_disruption(
    disruption_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    from fastapi import HTTPException
    import uuid
    result = await session.execute(
        select(Disruption).where(Disruption.id == uuid.UUID(disruption_id))
    )
    disruption = result.scalar_one_or_none()
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")
    return disruption


# ── Fleet ─────────────────────────────────────────────────────────────────────
fleet_router = APIRouter(prefix="/fleet", tags=["fleet"])


@fleet_router.get("", response_model=list[FleetRead])
async def list_fleet(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(select(Fleet).order_by(Fleet.vehicle_id))
    return result.scalars().all()


# ── Recommendations ───────────────────────────────────────────────────────────
recommendations_router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@recommendations_router.get("", response_model=list[RecommendationRead])
async def list_recommendations(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(
        select(Recommendation).order_by(Recommendation.created_at.desc())
    )
    return result.scalars().all()


# ── Audit ─────────────────────────────────────────────────────────────────────
audit_router = APIRouter(prefix="/audit", tags=["audit"])


@audit_router.get("", response_model=list[AuditRead])
async def list_audit(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(
        select(DecisionAudit).order_by(DecisionAudit.created_at.desc()).limit(500)
    )
    return result.scalars().all()


# ── Carriers ──────────────────────────────────────────────────────────────────
carriers_router = APIRouter(prefix="/carriers", tags=["carriers"])


@carriers_router.get("", response_model=list[CarrierRead])
async def list_carriers(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(select(Carrier).order_by(Carrier.name))
    return result.scalars().all()


# ── Routes ────────────────────────────────────────────────────────────────────
routes_router = APIRouter(prefix="/routes", tags=["routes"])


@routes_router.get("", response_model=list[RouteRead])
async def list_routes(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(select(Route).order_by(Route.code))
    return result.scalars().all()
