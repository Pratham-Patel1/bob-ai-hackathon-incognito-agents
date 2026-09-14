"""
Disruptions router — full Phase 2 implementation.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_async_db
from backend.models.disruption import Disruption
from backend.models.shipment import Shipment
from backend.models.fleet import Fleet
from backend.models.carrier import Carrier
from backend.models.route import Route
from backend.models.shipment_disruption import ShipmentDisruption
from backend.models.recommendation import Recommendation
from backend.schemas.disruption import DisruptionCreate, DisruptionRead
from backend.schemas.recommendation import RecommendationRead
from backend.utils.audit import write_audit
from backend.engines import disruption_impact, cascade_impact, recommendation_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/disruptions", tags=["disruptions"])


def _model_to_dict(obj: Any) -> dict:
    """Shallow conversion of an ORM model to a plain dict for engine input."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


async def _active_shipment_dicts(session: AsyncSession) -> list[dict[str, Any]]:
    """Load active shipment data, including the route code used by impact matching."""
    result = await session.execute(
        select(Shipment, Route.code)
        .join(Route, Shipment.route_id == Route.id)
        .where(Shipment.status.in_(["in_transit", "at_risk", "delayed"]))
    )
    return [
        {**_model_to_dict(shipment), "route_code": route_code}
        for shipment, route_code in result.all()
    ]


@router.get("", response_model=list[DisruptionRead])
async def list_disruptions(
    status: str | None = None,
    type: str | None = None,
    severity: str | None = None,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(Disruption).order_by(Disruption.created_at.desc())
    if status:
        query = query.where(Disruption.status == status)
    else:
        query = query.where(Disruption.status != "resolved")
    if type:
        query = query.where(Disruption.type == type)
    if severity:
        query = query.where(Disruption.severity == severity)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{disruption_id}", response_model=DisruptionRead)
async def get_disruption(
    disruption_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(
        select(Disruption).where(Disruption.id == uuid.UUID(disruption_id))
    )
    disruption = result.scalar_one_or_none()
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")
    return disruption


@router.post("", response_model=DisruptionRead, status_code=201)
async def create_disruption(
    payload: DisruptionCreate,
    x_operator_name: str = Header(default="system"),
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Create a disruption and trigger impact analysis."""
    disruption = Disruption(**payload.model_dump())
    session.add(disruption)
    await session.flush()  # get the generated ID

    # Trigger DisruptionImpactEngine
    active_shipments = await _active_shipment_dicts(session)

    disruption_dict = _model_to_dict(disruption)
    impact = disruption_impact.run(disruption_dict, active_shipments)

    # Persist shipment_disruptions rows (ON CONFLICT DO NOTHING via merge logic)
    for impacted in impact.impacted_shipments:
        # Check if link already exists
        existing = await session.execute(
            select(ShipmentDisruption).where(
                ShipmentDisruption.shipment_id == uuid.UUID(impacted.shipment_id),
                ShipmentDisruption.disruption_id == disruption.id,
            )
        )
        if existing.scalar_one_or_none() is None:
            link = ShipmentDisruption(
                shipment_id=uuid.UUID(impacted.shipment_id),
                disruption_id=disruption.id,
                impact_reason=impacted.impact_reason,
                distance_to_epicenter_km=impacted.distance_to_epicenter_km,
            )
            session.add(link)

    # Audit
    await write_audit(
        session=session,
        entity_type="disruption",
        entity_id=disruption.id,
        action="disruption_created",
        actor=x_operator_name,
        actor_type="human" if x_operator_name != "system" else "system",
        reasoning=f"Disruption '{disruption.title}' created. {impact.affected_count} shipments affected.",
        new_state=disruption_dict,
        extra_metadata={"affected_count": impact.affected_count},
    )

    await session.commit()
    await session.refresh(disruption)
    return disruption


@router.patch("/{disruption_id}/resolve", response_model=DisruptionRead)
async def resolve_disruption(
    disruption_id: str,
    x_operator_name: str = Header(default="system"),
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(
        select(Disruption).where(Disruption.id == uuid.UUID(disruption_id))
    )
    disruption = result.scalar_one_or_none()
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")

    prev_state = _model_to_dict(disruption)
    disruption.status = "resolved"
    disruption.actual_end_time = datetime.now(timezone.utc)

    await write_audit(
        session=session,
        entity_type="disruption",
        entity_id=disruption.id,
        action="disruption_resolved",
        actor=x_operator_name,
        actor_type="human" if x_operator_name != "system" else "system",
        reasoning=f"Disruption '{disruption.title}' marked as resolved.",
        previous_state=prev_state,
        new_state=_model_to_dict(disruption),
    )

    await session.commit()
    await session.refresh(disruption)
    return disruption


@router.get("/{disruption_id}/impact")
async def get_disruption_impact(
    disruption_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Run DisruptionImpactEngine and return affected shipments."""
    result = await session.execute(
        select(Disruption).where(Disruption.id == uuid.UUID(disruption_id))
    )
    disruption = result.scalar_one_or_none()
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")

    active_shipments = await _active_shipment_dicts(session)

    impact = disruption_impact.run(_model_to_dict(disruption), active_shipments)
    return {
        "disruption_id": disruption_id,
        "affected_count": impact.affected_count,
        "impacted_shipments": [
            {
                "shipment_id": i.shipment_id,
                "impact_reason": i.impact_reason,
                "distance_to_epicenter_km": i.distance_to_epicenter_km,
                "impact_score": i.impact_score,
                "impact_level": i.impact_level,
                "estimated_delay_hours": i.estimated_delay_hours,
                "factors": i.factors,
            }
            for i in impact.impacted_shipments
        ],
    }


@router.get("/{disruption_id}/affected-shipments")
async def get_affected_shipments(
    disruption_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Query shipment_disruptions join table for this disruption."""
    links_result = await session.execute(
        select(ShipmentDisruption).where(
            ShipmentDisruption.disruption_id == uuid.UUID(disruption_id)
        )
    )
    links = links_result.scalars().all()
    return [
        {
            "shipment_id": str(link.shipment_id),
            "disruption_id": str(link.disruption_id),
            "impact_reason": link.impact_reason,
            "distance_to_epicenter_km": float(link.distance_to_epicenter_km)
            if link.distance_to_epicenter_km
            else None,
            "created_at": link.created_at.isoformat() if link.created_at else None,
        }
        for link in links
    ]


@router.get("/{disruption_id}/cascade")
async def get_cascade_impact(
    disruption_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Run CascadingImpactEngine for this disruption."""
    result = await session.execute(
        select(Disruption).where(Disruption.id == uuid.UUID(disruption_id))
    )
    disruption = result.scalar_one_or_none()
    if not disruption:
        raise HTTPException(status_code=404, detail="Disruption not found")

    links_result = await session.execute(
        select(ShipmentDisruption).where(
            ShipmentDisruption.disruption_id == uuid.UUID(disruption_id)
        )
    )
    direct_ids = {str(link.shipment_id) for link in links_result.scalars().all()}

    all_shipments_result = await session.execute(select(Shipment))
    all_shipments = [_model_to_dict(s) for s in all_shipments_result.scalars().all()]

    all_fleet_result = await session.execute(select(Fleet))
    all_fleet = [_model_to_dict(f) for f in all_fleet_result.scalars().all()]

    cascade = cascade_impact.run(
        direct_shipment_ids=direct_ids,
        all_shipments=all_shipments,
        fleet=all_fleet,
    )
    return {
        "disruption_id": disruption_id,
        "direct_count": cascade.direct_count,
        "secondary_count": cascade.secondary_count,
        "total_value_at_risk_usd": cascade.total_value_at_risk_usd,
        "total_delay_hours_estimate": cascade.total_delay_hours_estimate,
        "explanation": cascade.explanation,
        "cascade_chain": [
            {
                "shipment_id": n.shipment_id,
                "tracking_number": n.tracking_number,
                "level": n.level,
                "impact_type": n.impact_type,
                "caused_by_shipment_id": n.caused_by_shipment_id,
                "estimated_delay_hours": n.estimated_delay_hours,
            }
            for n in cascade.cascade_chain
        ],
    }
