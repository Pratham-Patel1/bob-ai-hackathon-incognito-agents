"""
Audit router — read-only audit trail queries.
"""
from __future__ import annotations

import uuid
import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.models.decision_audit import DecisionAudit
from backend.schemas.audit import AuditRead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditRead])
async def list_audit(
    entity_type: str | None = None,
    actor_type: str | None = None,
    action: str | None = None,
    limit: int = 500,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(DecisionAudit).order_by(DecisionAudit.created_at.desc()).limit(limit)
    if entity_type:
        query = query.where(DecisionAudit.entity_type == entity_type)
    if actor_type:
        query = query.where(DecisionAudit.actor_type == actor_type)
    if action:
        query = query.where(DecisionAudit.action == action)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{entity_type}/{entity_id}", response_model=list[AuditRead])
async def get_entity_audit(
    entity_type: str,
    entity_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """History for a specific entity (e.g. /audit/shipment/{id})."""
    result = await session.execute(
        select(DecisionAudit)
        .where(
            DecisionAudit.entity_type == entity_type,
            DecisionAudit.entity_id == uuid.UUID(entity_id),
        )
        .order_by(DecisionAudit.created_at.asc())
    )
    return result.scalars().all()
