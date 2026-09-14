"""
Recommendations router — full Phase 2 with approval state machine.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.config import settings
from backend.models.recommendation import Recommendation
from backend.models.disruption import Disruption
from backend.models.shipment import Shipment
from backend.models.shipment_disruption import ShipmentDisruption
from backend.models.fleet import Fleet
from backend.models.carrier import Carrier
from backend.models.route import Route
from backend.models.temperature_log import TemperatureLog
from backend.schemas.recommendation import RecommendationRead, ApprovalAction
from backend.utils.audit import write_audit
from backend.engines import recommendation_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _model_to_dict(obj: Any) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def _rec_to_dict(rec: Any) -> dict:
    return {
        "id": str(rec.id),
        "type": rec.type,
        "priority": rec.priority,
        "status": rec.status,
        "title": rec.title,
        "reason": rec.reason,
        "requires_approval": rec.requires_approval,
    }


@router.get("", response_model=list[RecommendationRead])
async def list_recommendations(
    status: str | None = None,
    type: str | None = None,
    priority: str | None = None,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(Recommendation).order_by(Recommendation.created_at.desc())
    if status:
        query = query.where(Recommendation.status == status)
    if type:
        query = query.where(Recommendation.type == type)
    if priority:
        query = query.where(Recommendation.priority == priority)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{rec_id}", response_model=RecommendationRead)
async def get_recommendation(
    rec_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(
        select(Recommendation).where(Recommendation.id == uuid.UUID(rec_id))
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


@router.post("/generate")
async def generate_recommendations(
    disruption_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Trigger RecommendationEngine for a given disruption."""
    disruption_result = await session.execute(
        select(Disruption).where(Disruption.id == uuid.UUID(disruption_id))
    )
    disruption = disruption_result.scalar_one_or_none()
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")

    # Load all required data
    all_shipments_result = await session.execute(select(Shipment))
    all_shipments = [_model_to_dict(s) for s in all_shipments_result.scalars().all()]

    all_routes_result = await session.execute(select(Route))
    all_routes = [_model_to_dict(r) for r in all_routes_result.scalars().all()]

    all_carriers_result = await session.execute(select(Carrier))
    all_carrier_list = all_carriers_result.scalars().all()
    all_carriers = [_model_to_dict(c) for c in all_carrier_list]
    carriers_by_id = {str(c.id): _model_to_dict(c) for c in all_carrier_list}

    all_fleet_result = await session.execute(select(Fleet))
    all_fleet = [_model_to_dict(f) for f in all_fleet_result.scalars().all()]

    # Build temperature excursion map
    excursion_result = await session.execute(
        select(TemperatureLog.shipment_id).where(TemperatureLog.is_excursion == True).distinct()  # noqa: E712
    )
    excursion_shipment_ids = {str(row[0]) for row in excursion_result.all()}
    temperature_excursions = {sid: True for sid in excursion_shipment_ids}

    disruption_dict = _model_to_dict(disruption)

    orch = recommendation_engine.run(
        disruption=disruption_dict,
        all_shipments=all_shipments,
        all_routes=all_routes,
        all_carriers=all_carriers,
        all_fleet=all_fleet,
        temperature_excursions=temperature_excursions,
        carriers_by_id=carriers_by_id,
        approval_threshold_usd=settings.approval_threshold_usd,
    )

    # Persist recommendations
    created = []
    for candidate in orch.recommendations:
        rec = Recommendation(
            shipment_id=uuid.UUID(candidate.shipment_id) if candidate.shipment_id else None,
            disruption_id=uuid.UUID(candidate.disruption_id) if candidate.disruption_id else None,
            type=candidate.type,
            priority=candidate.priority,
            title=candidate.title,
            description=candidate.description,
            reason=candidate.reason,
            reasoning_factors=candidate.reasoning_factors,
            alternative_route_id=uuid.UUID(candidate.alternative_route_id)
            if candidate.alternative_route_id
            else None,
            alternative_carrier_id=uuid.UUID(candidate.alternative_carrier_id)
            if candidate.alternative_carrier_id
            else None,
            estimated_savings_usd=candidate.estimated_savings_usd,
            estimated_delay_reduction_hours=candidate.estimated_delay_reduction_hours,
            requires_approval=candidate.requires_approval,
            status="pending",
        )
        session.add(rec)
        await session.flush()

        await write_audit(
            session=session,
            entity_type="recommendation",
            entity_id=rec.id,
            action="rec_generated",
            actor="system",
            actor_type="system",
            reasoning=candidate.reason,
            new_state=_rec_to_dict(rec),
            extra_metadata={"disruption_id": disruption_id},
        )
        created.append(rec.id)

    await session.commit()
    return {
        "created_count": len(created),
        "recommendation_ids": [str(rid) for rid in created],
        "disruption_id": disruption_id,
        "affected_shipment_count": len(orch.affected_shipment_ids),
    }


# ── Approval state machine ────────────────────────────────────────────────────

@router.post("/{rec_id}/approve", response_model=RecommendationRead)
async def approve_recommendation(
    rec_id: str,
    payload: ApprovalAction,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    rec = await _get_rec_or_404(rec_id, session)
    if rec.status != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot approve: status is '{rec.status}'")

    prev = _rec_to_dict(rec)
    rec.status = "approved"
    rec.approved_by = payload.actor
    rec.approved_at = datetime.now(timezone.utc)

    await write_audit(
        session=session,
        entity_type="recommendation",
        entity_id=rec.id,
        action="rec_approved",
        actor=payload.actor,
        actor_type="human",
        reasoning=payload.notes or f"Approved by {payload.actor}",
        previous_state=prev,
        new_state=_rec_to_dict(rec),
    )
    await session.commit()
    await session.refresh(rec)
    return rec


@router.post("/{rec_id}/reject", response_model=RecommendationRead)
async def reject_recommendation(
    rec_id: str,
    payload: ApprovalAction,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    rec = await _get_rec_or_404(rec_id, session)
    if rec.status not in ("pending", "deferred"):
        raise HTTPException(status_code=409, detail=f"Cannot reject: status is '{rec.status}'")

    prev = _rec_to_dict(rec)
    rec.status = "rejected"

    await write_audit(
        session=session,
        entity_type="recommendation",
        entity_id=rec.id,
        action="rec_rejected",
        actor=payload.actor,
        actor_type="human",
        reasoning=payload.notes or f"Rejected by {payload.actor}",
        previous_state=prev,
        new_state=_rec_to_dict(rec),
    )
    await session.commit()
    await session.refresh(rec)
    return rec


@router.post("/{rec_id}/defer", response_model=RecommendationRead)
async def defer_recommendation(
    rec_id: str,
    payload: ApprovalAction,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    rec = await _get_rec_or_404(rec_id, session)
    if rec.status != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot defer: status is '{rec.status}'")

    prev = _rec_to_dict(rec)
    rec.status = "deferred"

    await write_audit(
        session=session,
        entity_type="recommendation",
        entity_id=rec.id,
        action="rec_deferred",
        actor=payload.actor,
        actor_type="human",
        reasoning=payload.notes or f"Deferred by {payload.actor}",
        previous_state=prev,
        new_state=_rec_to_dict(rec),
    )
    await session.commit()
    await session.refresh(rec)
    return rec


@router.post("/{rec_id}/implement", response_model=RecommendationRead)
async def implement_recommendation(
    rec_id: str,
    payload: ApprovalAction,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    rec = await _get_rec_or_404(rec_id, session)

    # State machine: requires_approval recs must be approved before implement
    if rec.requires_approval and rec.status != "approved":
        raise HTTPException(
            status_code=409,
            detail=f"This recommendation requires approval before implementation. Current status: '{rec.status}'",
        )
    if rec.status not in ("pending", "approved"):
        raise HTTPException(status_code=409, detail=f"Cannot implement: status is '{rec.status}'")

    prev = _rec_to_dict(rec)
    rec.status = "implemented"

    await write_audit(
        session=session,
        entity_type="recommendation",
        entity_id=rec.id,
        action="rec_implemented",
        actor=payload.actor,
        actor_type="human",
        reasoning=payload.notes or f"Implemented by {payload.actor}",
        previous_state=prev,
        new_state=_rec_to_dict(rec),
    )
    await session.commit()
    await session.refresh(rec)
    return rec


async def _get_rec_or_404(rec_id: str, session: AsyncSession) -> Recommendation:
    result = await session.execute(
        select(Recommendation).where(Recommendation.id == uuid.UUID(rec_id))
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec
