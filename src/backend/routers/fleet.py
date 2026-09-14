"""Fleet API router — list vehicles and fleet intelligence analytics."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.models.fleet import Fleet
from backend.models.shipment import Shipment
from backend.models.disruption import Disruption
from backend.schemas.fleet import FleetRead
from backend.utils.serializers import (
    fleet_to_dict,
    shipment_to_dict,
    disruption_to_dict,
)
from backend.engines.fleet_intelligence import analyse_fleet

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fleet", tags=["fleet"])


@router.get("", response_model=list[FleetRead])
async def list_fleet(
    status: str | None = Query(None, description="Filter by vehicle status (e.g. active, idle, available)"),
    is_refrigerated: bool | None = Query(None, description="Filter for reefer/refrigerated capability"),
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(Fleet).order_by(Fleet.vehicle_id)
    if status:
        query = query.where(Fleet.status == status)
    if is_refrigerated is not None:
        query = query.where(Fleet.temperature_capable == is_refrigerated)

    result = await session.execute(query)
    return result.scalars().all()


@router.get("/intelligence")
async def get_fleet_intelligence(
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Analyze fleet asset utilization, idle capacity, and repositioning opportunities."""
    fleet_res = await session.execute(select(Fleet))
    fleet_assets = [fleet_to_dict(f) for f in fleet_res.scalars().all()]

    shipments_res = await session.execute(
        select(Shipment).where(Shipment.status.in_(["in_transit", "at_risk", "delayed"]))
    )
    active_shipments = [shipment_to_dict(s) for s in shipments_res.scalars().all()]

    disr_res = await session.execute(select(Disruption).where(Disruption.status != "resolved"))
    active_disruptions = [disruption_to_dict(d) for d in disr_res.scalars().all()]

    res = analyse_fleet(
        fleet_vehicles=fleet_assets,
    )
    return {
        "summary": {
            "total_vehicles": res.summary.total_vehicles,
            "idle_count": res.summary.idle_count,
            "available_count": res.summary.available_count,
            "overloaded_count": res.summary.overloaded_count,
            "in_transit_count": res.summary.in_transit_count,
            "maintenance_count": res.summary.maintenance_count,
            "average_utilisation_percent": res.summary.average_utilisation_percent,
            "refrigerated_available": res.summary.refrigerated_available,
        },
        "idle_vehicles": [v.__dict__ for v in res.idle_vehicles],
        "available_vehicles": [v.__dict__ for v in res.available_vehicles],
        "overloaded_vehicles": [v.__dict__ for v in res.overloaded_vehicles],
        "repositioning_recommendations": [v.__dict__ for v in res.redeployment_candidates],
        "factors": res.factors,
    }
