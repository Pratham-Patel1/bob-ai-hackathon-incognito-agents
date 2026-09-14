"""
DigitalTwinEngine — in-memory what-if scenario simulation.

Pure Python — no FastAPI or SQLAlchemy imports.
Runs the full engine pipeline on in-memory data copies without persisting
any shipment state or recommendations.
Writes exactly ONE audit record (via the router after this call returns).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import disruption_impact
from . import shipment_risk
from . import predictive_risk
from . import cascade_impact
from . import business_impact
from . import recommendation_engine


@dataclass
class SimulationSummary:
    scenario_name: str
    disruption_type: str
    disruption_severity: str
    affected_radius_km: float
    horizon_hours: float
    total_affected_shipments: int
    total_secondary_shipments: int
    total_cargo_value_at_risk_usd: float
    total_cost_of_delay_usd: float
    penalty_exposure_usd: float
    sla_breach_count: int
    recommendation_count: int


@dataclass
class SimulationResult:
    summary: SimulationSummary
    affected_shipments: list[dict] = field(default_factory=list)
    risk_scores: dict[str, float] = field(default_factory=dict)   # shipment_id → combined score
    cascade_analysis: Any = None
    business_impact: Any = None
    top_recommendations: list[dict] = field(default_factory=list)  # serialized for JSON response


def run(
    scenario: dict[str, Any],
    all_shipments: list[dict[str, Any]],
    all_routes: list[dict[str, Any]],
    all_carriers: list[dict[str, Any]],
    all_fleet: list[dict[str, Any]],
    temperature_excursions: dict[str, bool],
    carriers_by_id: dict[str, dict[str, Any]],
    approval_threshold_usd: float = 50_000.0,
) -> SimulationResult:
    """
    Run a what-if simulation entirely in memory.

    Args:
        scenario: dict with keys:
            name (str), disruption_type (str), severity (str),
            epicenter_lat (float), epicenter_lng (float),
            affected_radius_km (float), affected_route_codes (list[str]),
            horizon_hours (float, default 72)
        all_shipments, all_routes, all_carriers, all_fleet: current state (read-only)
        temperature_excursions: shipment_id → has_excursion
        carriers_by_id: carrier lookup dict
        approval_threshold_usd: approval threshold for recommendation flags

    Returns:
        SimulationResult — pure in-memory, no DB writes.
    """
    horizon_hours = float(scenario.get("horizon_hours") or 72.0)

    # Build a hypothetical disruption dict (NOT persisted)
    hypothetical_disruption: dict[str, Any] = {
        "id": "simulation-hypothetical",
        "type": scenario.get("disruption_type", "weather"),
        "severity": scenario.get("severity", "high"),
        "title": scenario.get("name", "Hypothetical Disruption"),
        "description": "Simulated disruption for what-if analysis.",
        "affected_region": scenario.get("affected_region", "simulated"),
        "epicenter_lat": float(scenario.get("epicenter_lat", 0)),
        "epicenter_lng": float(scenario.get("epicenter_lng", 0)),
        "affected_radius_km": float(scenario.get("affected_radius_km", 100)),
        "affected_route_codes": list(scenario.get("affected_route_codes") or []),
        "status": "active",
    }

    # Run recommendation orchestrator on in-memory copies
    # (the orchestrator is pure Python; no side effects)
    orch_result = recommendation_engine.run(
        disruption=hypothetical_disruption,
        all_shipments=all_shipments,
        all_routes=all_routes,
        all_carriers=all_carriers,
        all_fleet=all_fleet,
        temperature_excursions=temperature_excursions,
        carriers_by_id=carriers_by_id,
        approval_threshold_usd=approval_threshold_usd,
    )

    # Collect risk scores
    risk_scores: dict[str, float] = {}
    if orch_result.impact_result:
        for impacted in orch_result.impact_result.impacted_shipments:
            sid = impacted.shipment_id
            # Run risk engine to get score
            shipment = next(
                (s for s in all_shipments if str(s["id"]) == sid), None
            )
            if shipment:
                carrier = carriers_by_id.get(str(shipment.get("carrier_id") or ""), {})
                det = shipment_risk.run(
                    shipment=shipment,
                    active_disruptions=[hypothetical_disruption],
                    temperature_excursion=temperature_excursions.get(sid, False),
                    carrier=carrier,
                )
                ml = predictive_risk.run(
                    shipment=shipment,
                    active_disruptions=[hypothetical_disruption],
                    carrier=carrier,
                )
                if ml.ml_score is not None:
                    combined = 0.6 * det.score + 0.4 * ml.ml_score
                else:
                    combined = det.score
                risk_scores[sid] = round(combined, 4)

    # Affected shipment summaries
    affected_summaries = [
        {
            "shipment_id": sid,
            "tracking_number": next(
                (s.get("tracking_number") for s in all_shipments if str(s["id"]) == sid),
                sid,
            ),
            "combined_risk_score": risk_scores.get(sid, 0.0),
        }
        for sid in orch_result.affected_shipment_ids
    ]

    # Cascade
    cascade = orch_result.cascade_result

    # Business impact
    biz = orch_result.business_impact_result
    cost_of_delay = biz.cost_of_delay_usd if biz else 0.0
    total_value = biz.total_cargo_value_at_risk_usd if biz else 0.0
    penalty = biz.penalty_exposure_usd if biz else 0.0
    sla_breaches = biz.sla_breach_count if biz else 0

    # Top recommendations (serialized)
    top_recs = [
        {
            "type": r.type,
            "priority": r.priority,
            "title": r.title,
            "reason": r.reason,
            "requires_approval": r.requires_approval,
            "estimated_savings_usd": r.estimated_savings_usd,
        }
        for r in orch_result.recommendations[:10]
    ]

    summary = SimulationSummary(
        scenario_name=scenario.get("name", "Unnamed"),
        disruption_type=hypothetical_disruption["type"],
        disruption_severity=hypothetical_disruption["severity"],
        affected_radius_km=hypothetical_disruption["affected_radius_km"],
        horizon_hours=horizon_hours,
        total_affected_shipments=len(orch_result.affected_shipment_ids),
        total_secondary_shipments=cascade.secondary_count if cascade else 0,
        total_cargo_value_at_risk_usd=total_value,
        total_cost_of_delay_usd=cost_of_delay,
        penalty_exposure_usd=penalty,
        sla_breach_count=sla_breaches,
        recommendation_count=len(orch_result.recommendations),
    )

    return SimulationResult(
        summary=summary,
        affected_shipments=affected_summaries,
        risk_scores=risk_scores,
        cascade_analysis=cascade,
        business_impact=biz,
        top_recommendations=top_recs,
    )
