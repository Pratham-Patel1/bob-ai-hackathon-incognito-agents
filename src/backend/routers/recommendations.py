"""Recommendations API router — query, generate, and approve/reject with audit logging."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_async_db
from backend.models.recommendation import Recommendation
from backend.models.shipment import Shipment
from backend.models.disruption import Disruption
from backend.models.route import Route
from backend.models.carrier import Carrier
from backend.models.fleet import Fleet
from backend.models.temperature_log import TemperatureLog
from backend.schemas.recommendation import (
    RecommendationRead,
    ApprovalAction,
)
from backend.utils.audit import write_audit
from backend.utils.serializers import (
    shipment_to_dict,
    disruption_to_dict,
    route_to_dict,
    carrier_to_dict,
    fleet_to_dict,
    temperature_log_to_dict,
)
from backend.engines.recommendation import synthesize_recommendation
from backend.engines.route_optimizer import optimize_routes
from backend.engines.carrier_recommender import recommend_carriers
from backend.engines.fleet_intelligence import analyse_fleet
from backend.engines.cold_chain_anomaly import analyze_cold_chain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationRead])
async def list_recommendations(
    status: str | None = Query(None, description="Filter by status (pending, approved, rejected)"),
    priority: str | None = Query(None, description="Filter by priority (low, medium, high, critical)"),
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(Recommendation).order_by(Recommendation.created_at.desc())
    if status:
        query = query.where(Recommendation.status == status)
    if priority:
        query = query.where(Recommendation.priority == priority)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/generate")
async def generate_recommendations(
    shipment_id: str | None = Query(None, description="Optional target shipment ID."),
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Generate recommendations using synthesize_recommendation and persist to database."""
    if shipment_id:
        try:
            s_uuid = uuid.UUID(shipment_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid shipment UUID format")
        s_query = select(Shipment).where(Shipment.id == s_uuid).options(
            selectinload(Shipment.carrier), selectinload(Shipment.route)
        )
    else:
        s_query = (
            select(Shipment)
            .where(Shipment.status.in_(["at_risk", "delayed", "in_transit"]))
            .order_by(Shipment.risk_score.desc())
            .limit(5)
            .options(selectinload(Shipment.carrier), selectinload(Shipment.route))
        )

    s_res = await session.execute(s_query)
    target_shipments = s_res.scalars().all()
    if not target_shipments:
        return {"status": "ok", "generated_count": 0, "recommendations": []}

    disr_res = await session.execute(select(Disruption).where(Disruption.status != "resolved"))
    active_disruptions = [disruption_to_dict(d) for d in disr_res.scalars().all()]
    active_disr_dict = active_disruptions[0] if active_disruptions else None

    routes_res = await session.execute(select(Route).where(Route.active == True))  # noqa: E712
    all_routes = [route_to_dict(r) for r in routes_res.scalars().all()]

    carriers_res = await session.execute(select(Carrier).where(Carrier.active == True))  # noqa: E712
    all_carriers = [carrier_to_dict(c) for c in carriers_res.scalars().all()]

    fleet_res = await session.execute(select(Fleet))
    all_fleet = [fleet_to_dict(f) for f in fleet_res.scalars().all()]

    persisted_recs: list[dict[str, Any]] = []

    for shipment in target_shipments:
        shipment_dict = shipment_to_dict(shipment)
        curr_route = route_to_dict(shipment.route) if shipment.route else None

        opt_context = {
            "shipment_priority": shipment_dict.get("priority", "medium"),
            "cargo_value_usd": shipment_dict.get("cargo_value_usd", 0.0),
            "temperature_sensitive": shipment_dict.get("temperature_required", False),
            "deadline_hours": 48.0,
        }
        ro_res = optimize_routes(
            routes=all_routes,
            optimization_context=opt_context,
        )

        shipment_ctx = {
            "required_capacity": (float(shipment_dict.get("weight_kg") or 5000.0) / 1000.0),
            "route_distance_km": float((curr_route.get("distance_km") if curr_route else 500.0) or 500.0),
            "requires_reefer": bool(shipment_dict.get("temperature_required", False)),
            "shipment_priority": shipment_dict.get("priority", "medium"),
        }
        cr_res = recommend_carriers(
            carriers=all_carriers,
            shipment_context=shipment_ctx,
        )

        fl_res = analyse_fleet(
            fleet_vehicles=all_fleet,
            request_context={
                "epicenter_lat": active_disr_dict.get("latitude") if active_disr_dict else None,
                "epicenter_lng": active_disr_dict.get("longitude") if active_disr_dict else None,
                "required_capacity": shipment.weight_kg / 1000.0 if shipment.weight_kg else 1.0,
                "requires_reefer": shipment.temperature_required or False,
            },
        )

        cold_res = None
        if shipment.temperature_required:
            logs_res = await session.execute(
                select(TemperatureLog).where(TemperatureLog.shipment_id == shipment.id)
            )
            logs = [temperature_log_to_dict(l) for l in logs_res.scalars().all()]
            cold_res = analyze_cold_chain(temperature_readings=logs, shipment_config=shipment_dict)

        bundle = synthesize_recommendation(
            shipment_context=shipment_dict,
            cold_chain_result=cold_res,
            route_result=ro_res,
            carrier_result=cr_res,
            fleet_result=fl_res,
        )

        alt_r_id = None
        if bundle.target_route_id:
            try:
                alt_r_id = uuid.UUID(str(bundle.target_route_id))
            except ValueError:
                pass

        alt_c_id = None
        if bundle.target_carrier_id:
            try:
                alt_c_id = uuid.UUID(str(bundle.target_carrier_id))
            except ValueError:
                pass

        now = datetime.now(timezone.utc)
        title_action = bundle.recommended_action.replace("_", " ").title()
        action_type = bundle.recommended_action.lower()
        urgency_level = bundle.urgency_level.lower()
        desc = "; ".join(bundle.reasons) if bundle.reasons else f"Recommended action {bundle.recommended_action} for shipment {shipment.tracking_number}."
        rec_title = f"{title_action} — {shipment.tracking_number}"

        req_approval = urgency_level in ("high", "critical") or action_type in ("reroute", "carrier_swap")

        disr_id = None
        if active_disr_dict and active_disr_dict.get("id"):
            try:
                disr_id = uuid.UUID(str(active_disr_dict["id"]))
            except ValueError:
                pass

        rec_row = Recommendation(
            shipment_id=shipment.id,
            disruption_id=disr_id,
            type=action_type,
            priority=urgency_level,
            title=rec_title,
            description=desc,
            reason=bundle.reasons[0] if bundle.reasons else "Disruption resilience action",
            reasoning_factors=bundle.reasons,
            alternative_route_id=alt_r_id,
            alternative_carrier_id=alt_c_id,
            estimated_savings_usd=bundle.business_impact.get("savings_usd") if bundle.business_impact else None,
            estimated_delay_reduction_hours=bundle.business_impact.get("delay_reduction_hours") if bundle.business_impact else None,
            requires_approval=req_approval,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        session.add(rec_row)
        await session.flush()

        persisted_recs.append({
            "id": str(rec_row.id),
            "shipment_id": str(shipment.id),
            "type": rec_row.type,
            "priority": rec_row.priority,
            "title": rec_row.title,
            "status": rec_row.status,
        })

    await session.commit()
    return {
        "status": "ok",
        "generated_count": len(persisted_recs),
        "recommendations": persisted_recs,
    }


@router.post("/{recommendation_id}/approve", response_model=RecommendationRead)
async def approve_recommendation(
    recommendation_id: str,
    action: ApprovalAction,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Approve a recommendation, transitioning state to APPROVED and logging to DecisionAudit."""
    try:
        r_id = uuid.UUID(recommendation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recommendation UUID format")

    result = await session.execute(select(Recommendation).where(Recommendation.id == r_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    if rec.status == "approved":
        raise HTTPException(status_code=400, detail="Recommendation is already approved")

    prev_state = {"status": rec.status, "approved_by": rec.approved_by}
    rec.status = "approved"
    rec.approved_by = action.actor
    rec.approved_at = datetime.now(timezone.utc)
    new_state = {"status": rec.status, "approved_by": rec.approved_by, "notes": action.notes}

    await write_audit(
        session=session,
        entity_type="recommendation",
        entity_id=rec.id,
        action="rec_approved",
        actor=action.actor,
        actor_type="human",
        reasoning=action.notes or f"Approved recommendation {rec.title}",
        previous_state=prev_state,
        new_state=new_state,
        extra_metadata={"recommendation_type": rec.type, "priority": rec.priority},
    )

    await session.commit()
    await session.refresh(rec)
    return rec


@router.post("/{recommendation_id}/reject", response_model=RecommendationRead)
async def reject_recommendation(
    recommendation_id: str,
    action: ApprovalAction,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Reject a recommendation, transitioning state to REJECTED and logging to DecisionAudit."""
    try:
        r_id = uuid.UUID(recommendation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recommendation UUID format")

    result = await session.execute(select(Recommendation).where(Recommendation.id == r_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    prev_state = {"status": rec.status, "approved_by": rec.approved_by}
    rec.status = "rejected"
    rec.approved_by = action.actor
    rec.approved_at = datetime.now(timezone.utc)
    new_state = {"status": rec.status, "approved_by": rec.approved_by, "notes": action.notes}

    await write_audit(
        session=session,
        entity_type="recommendation",
        entity_id=rec.id,
        action="rec_rejected",
        actor=action.actor,
        actor_type="human",
        reasoning=action.notes or f"Rejected recommendation {rec.title}",
        previous_state=prev_state,
        new_state=new_state,
        extra_metadata={"recommendation_type": rec.type, "priority": rec.priority},
    )

    await session.commit()
    await session.refresh(rec)
    return rec
