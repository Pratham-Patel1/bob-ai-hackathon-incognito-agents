"""Audit API router — immutable decision and recommendation logs."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.models.decision_audit import DecisionAudit
from backend.schemas.audit import AuditRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditRead])
async def list_audit(
    limit: int = Query(100, ge=1, le=500),
    entity_type: str | None = Query(None, description="Filter by entity type (recommendation, shipment, simulation)"),
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(DecisionAudit).order_by(DecisionAudit.created_at.desc())
    if entity_type:
        query = query.where(DecisionAudit.entity_type == entity_type)
    query = query.limit(limit)

    result = await session.execute(query)
    return result.scalars().all()
