"""Routes API router — list and retrieve supply chain route geometries."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.models.route import Route
from backend.schemas.route import RouteRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("", response_model=list[RouteRead])
async def list_routes(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(select(Route).order_by(Route.code))
    return result.scalars().all()


@router.get("/{route_id}", response_model=RouteRead)
async def get_route(
    route_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    try:
        r_id = uuid.UUID(route_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid route UUID format")

    result = await session.execute(select(Route).where(Route.id == r_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route
