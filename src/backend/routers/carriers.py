"""Carriers API router — list and retrieve carriers."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.models.carrier import Carrier
from backend.schemas.carrier import CarrierRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/carriers", tags=["carriers"])


@router.get("", response_model=list[CarrierRead])
async def list_carriers(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(select(Carrier).order_by(Carrier.name))
    return result.scalars().all()


@router.get("/{carrier_id}", response_model=CarrierRead)
async def get_carrier(
    carrier_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    try:
        c_id = uuid.UUID(carrier_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid carrier UUID format")

    result = await session.execute(select(Carrier).where(Carrier.id == c_id))
    carrier = result.scalar_one_or_none()
    if not carrier:
        raise HTTPException(status_code=404, detail="Carrier not found")
    return carrier
