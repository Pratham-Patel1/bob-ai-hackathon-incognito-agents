"""Disruptions API router — list, details, and disruption impact evaluation."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.models.disruption import Disruption
from backend.models.shipment import Shipment
from backend.models.route import Route
from backend.schemas.disruption import DisruptionRead
from backend.utils.serializers import (
    disruption_to_dict,
    shipment_to_dict,
    route_to_dict,
)
from backend.engines.disruption_impact import DisruptionImpactEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/disruptions", tags=["disruptions"])


@router.get("", response_model=list[DisruptionRead])
async def list_disruptions(
    severity: str | None = Query(None, description="Filter by severity ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')"),
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(Disruption).where(Disruption.status != "resolved").order_by(Disruption.created_at.desc())
    if severity:
        query = query.where(Disruption.severity.ilike(severity))
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{disruption_id}", response_model=DisruptionRead)
async def get_disruption(
    disruption_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    try:
        d_id = uuid.UUID(disruption_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid disruption UUID format")

    result = await session.execute(select(Disruption).where(Disruption.id == d_id))
    disruption = result.scalar_one_or_none()
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")
    return disruption


@router.get("/{disruption_id}/impact")
async def get_disruption_impact(
    disruption_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Execute DisruptionImpactEngine to evaluate all shipments affected by this disruption."""
    try:
        d_id = uuid.UUID(disruption_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid disruption UUID format")

    result = await session.execute(select(Disruption).where(Disruption.id == d_id))
    disruption = result.scalar_one_or_none()
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")

    # Fetch all active shipments
    shipments_res = await session.execute(
        select(Shipment).where(Shipment.status.in_(["in_transit", "at_risk", "delayed", "held"]))
    )
    shipments = [shipment_to_dict(s) for s in shipments_res.scalars().all()]

    # Fetch routes map
    routes_res = await session.execute(select(Route))
    routes_map = {str(r.id): route_to_dict(r) for r in routes_res.scalars().all()}

    disruption_dict = disruption_to_dict(disruption)
    engine = DisruptionImpactEngine()
    impact = engine.evaluate_disruption(
        disruption=disruption_dict,
        shipments=shipments,
        routes_map=routes_map,
    )
    return impact
