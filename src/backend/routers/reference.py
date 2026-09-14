"""
Carriers and Routes reference data routers.
"""
from __future__ import annotations

import uuid
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.models.carrier import Carrier
from backend.models.route import Route
from backend.schemas.carrier import CarrierRead
from backend.schemas.route import RouteRead

logger = logging.getLogger(__name__)

carriers_router = APIRouter(prefix="/carriers", tags=["carriers"])
routes_router = APIRouter(prefix="/routes", tags=["routes"])


@carriers_router.get("", response_model=list[CarrierRead])
async def list_carriers(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(select(Carrier).where(Carrier.active == True).order_by(Carrier.name))  # noqa: E712
    return result.scalars().all()


@carriers_router.get("/{carrier_id}", response_model=CarrierRead)
async def get_carrier(
    carrier_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(
        select(Carrier).where(Carrier.id == uuid.UUID(carrier_id))
    )
    carrier = result.scalar_one_or_none()
    if not carrier:
        raise HTTPException(status_code=404, detail="Carrier not found")
    return carrier


@routes_router.get("", response_model=list[RouteRead])
async def list_routes(
    mode: str | None = None,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(Route).where(Route.active == True).order_by(Route.code)  # noqa: E712
    if mode:
        query = query.where(Route.mode == mode)
    result = await session.execute(query)
    return result.scalars().all()


@routes_router.get("/{route_id}", response_model=RouteRead)
async def get_route(
    route_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(
        select(Route).where(Route.id == uuid.UUID(route_id))
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@routes_router.get("/{route_id}/alternatives", response_model=list[RouteRead])
async def get_route_alternatives(
    route_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Find alternative routes for the same origin/destination pair."""
    route_result = await session.execute(
        select(Route).where(Route.id == uuid.UUID(route_id))
    )
    route = route_result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    result = await session.execute(
        select(Route).where(
            Route.origin == route.origin,
            Route.destination == route.destination,
            Route.id != route.id,
            Route.active == True,  # noqa: E712
        ).order_by(Route.reliability_score.desc())
    )
    return result.scalars().all()
