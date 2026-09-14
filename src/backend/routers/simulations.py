"""Simulations API router — Digital Twin in-memory what-if route simulation and scenario testing."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_async_db
from backend.models.shipment import Shipment
from backend.models.route import Route
from backend.models.carrier import Carrier
from backend.models.disruption import Disruption
from backend.models.fleet import Fleet
from backend.schemas.simulation import SimulationScenario, SimulationResult
from backend.utils.serializers import (
    shipment_to_dict,
    route_to_dict,
    carrier_to_dict,
    disruption_to_dict,
    fleet_to_dict,
)
from backend.engines.digital_twin import run_digital_twin
from backend.engines.cascading_impact import compute_cascade_impact
from backend.engines.business_impact import calculate_business_impact
from backend.engines.disruption_impact import DisruptionImpactEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulations", tags=["simulations"])


class RouteSimulationRequest(BaseModel):
    shipment_id: str
    candidate_route_id: str
    candidate_carrier_id: str | None = None


@router.post("/route")
async def simulate_route(
    req: RouteSimulationRequest,
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Run in-memory Digital Twin simulation comparing baseline vs candidate reroute."""
    try:
        s_id = uuid.UUID(req.shipment_id)
        r_id = uuid.UUID(req.candidate_route_id)
        c_id = uuid.UUID(req.candidate_carrier_id) if req.candidate_carrier_id else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format provided")

    s_res = await session.execute(
        select(Shipment)
        .where(Shipment.id == s_id)
        .options(
            selectinload(Shipment.carrier),
            selectinload(Shipment.route),
        )
    )
    shipment = s_res.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    r_res = await session.execute(select(Route).where(Route.id == r_id))
    candidate_route = r_res.scalar_one_or_none()
    if not candidate_route:
        raise HTTPException(status_code=404, detail="Candidate route not found")

    candidate_carrier = None
    if c_id:
        c_res = await session.execute(select(Carrier).where(Carrier.id == c_id))
        candidate_carrier = c_res.scalar_one_or_none()

    disr_res = await session.execute(select(Disruption).where(Disruption.status != "resolved"))
    active_disruptions = [disruption_to_dict(d) for d in disr_res.scalars().all()]

    shipment_dict = shipment_to_dict(shipment)
    cand_route_dict = route_to_dict(candidate_route)
    cand_carrier_dict = carrier_to_dict(candidate_carrier) if candidate_carrier else None
    curr_route_dict = route_to_dict(shipment.route) if shipment.route else None
    curr_carrier_dict = carrier_to_dict(shipment.carrier) if shipment.carrier else None

    # Cascade analysis
    other_shipments_res = await session.execute(
        select(Shipment)
        .where(Shipment.id != s_id)
        .where(Shipment.status.in_(["in_transit", "at_risk"]))
        .limit(20)
    )
    downstream = [shipment_to_dict(s) for s in other_shipments_res.scalars().all()]

    fleet_res = await session.execute(select(Fleet).limit(20))
    fleet_assets = [fleet_to_dict(f) for f in fleet_res.scalars().all()]

    cascade_res = compute_cascade_impact(
        affected_shipment=shipment_dict,
        all_shipments=downstream,
        all_vehicles=fleet_assets,
    )
    cascade_out = {
        "primary_shipment_id": str(shipment.id),
        "cascade_depth": cascade_res.cascade_depth,
        "total_affected_count": cascade_res.total_affected_count,
        "directly_affected_shipment_ids": cascade_res.directly_affected_shipment_ids,
        "potentially_delayed_shipments": [s.__dict__ for s in cascade_res.potentially_delayed_shipments],
        "vehicle_conflicts": [v.__dict__ for v in cascade_res.vehicle_conflicts],
        "factors": cascade_res.factors,
    }

    cand_route_id = str(candidate_route.id)
    cand_carrier_id = str(candidate_carrier.id) if candidate_carrier else ""

    current_scenario = {
        "shipment_id": str(shipment.id),
        "tracking_number": shipment.tracking_number,
        "current_route_id": str(shipment.route_id) if shipment.route_id else "",
        "current_carrier_id": str(shipment.carrier_id) if shipment.carrier_id else "",
        "estimated_hours": curr_route_dict.get("estimated_hours", 8.0) if curr_route_dict else 8.0,
        "total_cost_usd": curr_route_dict.get("total_cost_usd", 1000.0) if curr_route_dict else 1000.0,
        "risk_score": 30.0,
        "on_time_probability": 0.85,
    }
    simulated_changes = {
        "simulated_route_id": cand_route_id,
        "simulated_carrier_id": cand_carrier_id,
        "simulated_estimated_hours": cand_route_dict.get("estimated_hours", curr_route_dict.get("estimated_hours", 8.0) if curr_route_dict else 8.0),
        "simulated_total_cost_usd": cand_route_dict.get("total_cost_usd", curr_route_dict.get("total_cost_usd", 1000.0) if curr_route_dict else 1000.0),
        "simulated_risk_score": 15.0,
        "simulated_on_time_probability": 0.95,
    }

    twin_res = run_digital_twin(
        current_scenario=current_scenario,
        simulated_changes=simulated_changes,
    )

    alt_cost = cand_route_dict.get("total_cost_usd")
    disr_ctx = dict(active_disruptions[0]) if active_disruptions else {}
    disr_ctx["delay_hours"] = max(0.0, twin_res.delta.hours_delta)
    biz_res = calculate_business_impact(
        shipment=shipment_dict,
        disruption_context=disr_ctx,
        alternative_route_cost_usd=alt_cost,
    )
    biz_out = {
        "cargo_value_at_risk_usd": biz_res.cargo_value_at_risk_usd,
        "sla_penalty_usd": biz_res.sla_penalty_usd,
        "extra_transport_cost_usd": biz_res.extra_transport_cost_usd,
        "total_financial_exposure_usd": biz_res.total_financial_exposure_usd,
        "risk_percentage": biz_res.risk_percentage,
        "breakdown": biz_res.breakdown,
        "factors": biz_res.factors,
    }

    return {
        "shipment_id": str(shipment.id),
        "baseline": twin_res.current.__dict__,
        "simulated": twin_res.simulated.__dict__,
        "delta": twin_res.delta.__dict__,
        "recommendation": twin_res.recommendation,
        "confidence": twin_res.confidence,
        "business_impact": biz_out,
        "cascading_impact": cascade_out,
        "factors": twin_res.factors,
    }


@router.post("/scenario", response_model=SimulationResult)
async def simulate_scenario(
    scenario: SimulationScenario,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Run a multi-shipment what-if scenario simulation across the network."""
    synth_disruption = {
        "id": "scenario-synth-01",
        "title": scenario.title,
        "type": scenario.disruption_type,
        "severity": scenario.disruption_severity,
        "status": "active",
        "epicenter_lat": scenario.epicenter_lat,
        "epicenter_lng": scenario.epicenter_lng,
        "radius_km": scenario.affected_radius_km,
        "affected_routes": scenario.affected_route_codes,
        "estimated_delay_hours": 12.0,
    }

    shipments_res = await session.execute(
        select(Shipment).where(Shipment.status.in_(["in_transit", "at_risk"]))
    )
    shipments = [shipment_to_dict(s) for s in shipments_res.scalars().all()]

    routes_res = await session.execute(select(Route))
    routes_map = {str(r.id): route_to_dict(r) for r in routes_res.scalars().all()}

    fleet_res = await session.execute(select(Fleet).limit(20))
    fleet_assets = [fleet_to_dict(f) for f in fleet_res.scalars().all()]

    impact_engine = DisruptionImpactEngine()
    impact_res = impact_engine.evaluate_disruption(
        disruption=synth_disruption,
        shipments=shipments,
        routes_map=routes_map,
    )

    affected_shipments = impact_res.get("affected_shipments", [])
    affected_count = len(affected_shipments)

    risk_scores = [
        {
            "shipment_id": a["shipment_id"],
            "impact_score": a["impact_score"],
            "impact_level": a["impact_level"],
            "estimated_delay_hours": a["estimated_delay_hours"],
            "factors": a["factors"],
        }
        for a in affected_shipments
    ]

    cascade_out = None
    if affected_shipments:
        top_s_id = affected_shipments[0]["shipment_id"]
        top_s = next((s for s in shipments if s["id"] == top_s_id), None)
        if top_s:
            casc_res = compute_cascade_impact(
                affected_shipment=top_s,
                all_shipments=[s for s in shipments if s["id"] != top_s_id],
                all_vehicles=fleet_assets,
            )
            cascade_out = {
                "primary_shipment_id": top_s_id,
                "cascade_depth": casc_res.cascade_depth,
                "total_affected_count": casc_res.total_affected_count,
                "directly_affected_shipment_ids": casc_res.directly_affected_shipment_ids,
                "potentially_delayed_shipments": [s.__dict__ for s in casc_res.potentially_delayed_shipments],
                "vehicle_conflicts": [v.__dict__ for v in casc_res.vehicle_conflicts],
                "factors": casc_res.factors,
            }

    return SimulationResult(
        scenario_summary={
            "title": scenario.title,
            "disruption_type": scenario.disruption_type,
            "severity": scenario.disruption_severity,
            "epicenter": {"lat": scenario.epicenter_lat, "lng": scenario.epicenter_lng},
            "radius_km": scenario.affected_radius_km,
        },
        affected_shipment_count=affected_count,
        risk_scores=risk_scores,
        cascade_analysis=cascade_out,
        business_impact={"scenario_projected_loss_usd": sum(a["impact_score"] * 100 for a in affected_shipments)},
        top_recommendations=[],
    )
