"""
Simulation router — Digital Twin what-if scenarios.
"""
from __future__ import annotations

import uuid
import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.config import settings
from backend.models.shipment import Shipment
from backend.models.fleet import Fleet
from backend.models.carrier import Carrier
from backend.models.route import Route
from backend.models.temperature_log import TemperatureLog
from backend.schemas.simulation import SimulationScenario
from backend.utils.audit import write_audit
from backend.engines import digital_twin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulation", tags=["simulation"])


def _model_to_dict(obj: Any) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.post("/run")
async def run_simulation(
    scenario: SimulationScenario,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Run a what-if Digital Twin simulation.
    Returns full result as JSON — no shipment state is modified.
    Writes exactly one audit record for traceability.
    """
    # Load current operational data (read-only)
    all_shipments_result = await session.execute(
        select(Shipment).where(Shipment.status.in_(["in_transit", "at_risk", "delayed"]))
    )
    all_shipments_objs = all_shipments_result.scalars().all()

    # If specific shipment_ids provided, filter to those
    if scenario.shipment_ids:
        sid_set = set(scenario.shipment_ids)
        all_shipments_objs = [s for s in all_shipments_objs if str(s.id) in sid_set]

    all_shipments = [_model_to_dict(s) for s in all_shipments_objs]

    all_routes_result = await session.execute(select(Route))
    all_routes = [_model_to_dict(r) for r in all_routes_result.scalars().all()]

    all_carriers_result = await session.execute(select(Carrier))
    all_carrier_list = all_carriers_result.scalars().all()
    all_carriers = [_model_to_dict(c) for c in all_carrier_list]
    carriers_by_id = {str(c.id): _model_to_dict(c) for c in all_carrier_list}

    all_fleet_result = await session.execute(select(Fleet))
    all_fleet = [_model_to_dict(f) for f in all_fleet_result.scalars().all()]

    excursion_result = await session.execute(
        select(TemperatureLog.shipment_id).where(TemperatureLog.is_excursion == True).distinct()  # noqa: E712
    )
    excursion_ids = {str(row[0]) for row in excursion_result.all()}
    temperature_excursions = {sid: True for sid in excursion_ids}

    # Build scenario dict for engine
    scenario_dict = {
        "name": scenario.title,
        "disruption_type": scenario.disruption_type,
        "severity": scenario.disruption_severity,
        "epicenter_lat": scenario.epicenter_lat,
        "epicenter_lng": scenario.epicenter_lng,
        "affected_radius_km": scenario.affected_radius_km,
        "affected_route_codes": scenario.affected_route_codes,
        "horizon_hours": 72,
    }

    sim_result = digital_twin.run(
        scenario=scenario_dict,
        all_shipments=all_shipments,
        all_routes=all_routes,
        all_carriers=all_carriers,
        all_fleet=all_fleet,
        temperature_excursions=temperature_excursions,
        carriers_by_id=carriers_by_id,
        approval_threshold_usd=settings.approval_threshold_usd,
    )

    # Write exactly one audit record for the simulation run
    sim_audit_id = uuid.uuid4()
    await write_audit(
        session=session,
        entity_type="simulation",
        entity_id=sim_audit_id,
        action="simulation_run",
        actor="system",
        actor_type="system",
        reasoning=f"What-if simulation: '{scenario.title}' — {sim_result.summary.total_affected_shipments} shipments affected.",
        new_state=scenario_dict,
        extra_metadata={
            "total_affected": sim_result.summary.total_affected_shipments,
            "total_secondary": sim_result.summary.total_secondary_shipments,
            "total_value_at_risk": sim_result.summary.total_cargo_value_at_risk_usd,
            "recommendation_count": sim_result.summary.recommendation_count,
        },
    )
    await session.commit()

    # Serialize result
    summary = sim_result.summary
    return {
        "scenario_summary": {
            "name": summary.scenario_name,
            "disruption_type": summary.disruption_type,
            "severity": summary.disruption_severity,
            "affected_radius_km": summary.affected_radius_km,
            "horizon_hours": summary.horizon_hours,
            "total_affected_shipments": summary.total_affected_shipments,
            "total_secondary_shipments": summary.total_secondary_shipments,
            "total_cargo_value_at_risk_usd": summary.total_cargo_value_at_risk_usd,
            "total_cost_of_delay_usd": summary.total_cost_of_delay_usd,
            "penalty_exposure_usd": summary.penalty_exposure_usd,
            "sla_breach_count": summary.sla_breach_count,
            "recommendation_count": summary.recommendation_count,
        },
        "affected_shipment_count": len(sim_result.affected_shipments),
        "risk_scores": [
            {"shipment_id": k, "combined_risk_score": v}
            for k, v in sim_result.risk_scores.items()
        ],
        "cascade_analysis": {
            "direct_count": sim_result.cascade_analysis.direct_count,
            "secondary_count": sim_result.cascade_analysis.secondary_count,
            "explanation": sim_result.cascade_analysis.explanation,
        } if sim_result.cascade_analysis else None,
        "business_impact": {
            "total_cargo_value_at_risk_usd": sim_result.business_impact.total_cargo_value_at_risk_usd,
            "cost_of_delay_usd": sim_result.business_impact.cost_of_delay_usd,
            "penalty_exposure_usd": sim_result.business_impact.penalty_exposure_usd,
            "sla_breach_count": sim_result.business_impact.sla_breach_count,
            "avg_delay_hours": sim_result.business_impact.avg_delay_hours,
        } if sim_result.business_impact else None,
        "top_recommendations": sim_result.top_recommendations,
    }
