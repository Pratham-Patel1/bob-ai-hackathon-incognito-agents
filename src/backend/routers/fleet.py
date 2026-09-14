"""
Fleet router — full Phase 2 implementation.
"""
from __future__ import annotations

import uuid
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.models.fleet import Fleet
from backend.models.shipment import Shipment
from backend.schemas.fleet import FleetRead
from backend.engines import fleet_intelligence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fleet", tags=["fleet"])


def _model_to_dict(obj: Any) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("", response_model=list[FleetRead])
async def list_fleet(
    status: str | None = None,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(Fleet).order_by(Fleet.vehicle_id)
    if status:
        query = query.where(Fleet.status == status)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/idle", response_model=list[FleetRead])
async def list_idle_fleet(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Vehicles with utilization_pct < 20% and status = active."""
    result = await session.execute(
        select(Fleet).where(
            Fleet.status == "active",
            Fleet.utilization_pct < 20,
        ).order_by(Fleet.utilization_pct)
    )
    return result.scalars().all()


@router.get("/overloaded", response_model=list[FleetRead])
async def list_overloaded_fleet(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Vehicles with utilization_pct > 95%."""
    result = await session.execute(
        select(Fleet).where(Fleet.utilization_pct > 95).order_by(Fleet.utilization_pct.desc())
    )
    return result.scalars().all()


@router.get("/redeployment-suggestions")
async def get_redeployment_suggestions(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """FleetIntelligenceEngine: find idle vehicles + match to needy shipments."""
    fleet_result = await session.execute(select(Fleet))
    all_fleet = [_model_to_dict(f) for f in fleet_result.scalars().all()]

    # Needy shipments: delayed/at_risk without fleet assignment or in disruption
    needy_result = await session.execute(
        select(Shipment).where(
            Shipment.status.in_(["delayed", "at_risk"]),
        )
    )
    needy_shipments = [_model_to_dict(s) for s in needy_result.scalars().all()]

    # Fleet analysis
    analysis = fleet_intelligence.analyse_fleet(all_fleet)
    suggestions = fleet_intelligence.suggest_redeployments(all_fleet, needy_shipments)

    return {
        "fleet_analysis": {
            "idle_count": analysis.idle_count,
            "overloaded_count": analysis.overloaded_count,
            "idle_vehicle_ids": analysis.idle_vehicle_ids,
            "overloaded_vehicle_ids": analysis.overloaded_vehicle_ids,
            "utilization_histogram": analysis.utilization_histogram,
        },
        "redeployment_suggestions": [
            {
                "vehicle_id": s.vehicle_id,
                "target_shipment_id": s.target_shipment_id,
                "distance_km": s.distance_km,
                "reason": s.reason,
            }
            for s in suggestions
        ],
    }


@router.get("/{fleet_id}", response_model=FleetRead)
async def get_fleet_vehicle(
    fleet_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(
        select(Fleet).where(Fleet.id == uuid.UUID(fleet_id))
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Fleet vehicle not found")
    return vehicle
