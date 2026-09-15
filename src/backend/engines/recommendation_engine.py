"""
RecommendationEngine — orchestrator for all business engines.

Pure Python — no FastAPI or SQLAlchemy imports.
Accepts pre-loaded data dicts; returns a list of Recommendation dicts
ready for DB persistence by the router.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import disruption_impact
from . import shipment_risk
from . import predictive_risk
from . import cold_chain
from . import fleet_intelligence
from . import route_optimizer
from . import carrier_recommender
from . import cascade_impact
from . import business_impact


@dataclass
class RecommendationCandidate:
    """Intermediate representation before DB persistence."""
    shipment_id: str | None
    disruption_id: str | None
    type: str                    # reroute | carrier_change | fleet_redeploy | hold | expedite | escalate
    priority: str                # low | medium | high | critical
    title: str
    description: str
    reason: str                  # enforced non-empty
    reasoning_factors: list[dict]
    alternative_route_id: str | None = None
    alternative_carrier_id: str | None = None
    estimated_savings_usd: float = 0.0
    estimated_delay_reduction_hours: float = 0.0
    requires_approval: bool = False


@dataclass
class OrchestratorResult:
    recommendations: list[RecommendationCandidate] = field(default_factory=list)
    impact_result: Any = None
    cascade_result: Any = None
    business_impact_result: Any = None
    affected_shipment_ids: list[str] = field(default_factory=list)


def run(
    disruption: dict[str, Any],
    all_shipments: list[dict[str, Any]],
    all_routes: list[dict[str, Any]],
    all_carriers: list[dict[str, Any]],
    all_fleet: list[dict[str, Any]],
    temperature_excursions: dict[str, bool],  # shipment_id → has_excursion
    carriers_by_id: dict[str, dict[str, Any]],
    approval_threshold_usd: float = 50_000.0,
) -> OrchestratorResult:
    """
    Orchestrate all engines for one disruption.

    Args:
        disruption: disruption dict
        all_shipments: list of all active shipment dicts
        all_routes: list of all route dicts
        all_carriers: list of all carrier dicts
        all_fleet: list of all fleet dicts
        temperature_excursions: map of shipment_id → True if active excursion
        carriers_by_id: pre-built carrier lookup dict
        approval_threshold_usd: cargo value threshold for human approval

    Returns:
        OrchestratorResult
    """
    result = OrchestratorResult()

    # ── 1. Disruption impact ─────────────────────────────────────────────────
    active_shipments = [
        s for s in all_shipments
        if s.get("status") in ("in_transit", "at_risk", "delayed")
    ]
    impact = disruption_impact.run(disruption, active_shipments)
    result.impact_result = impact
    result.affected_shipment_ids = [i.shipment_id for i in impact.impacted_shipments]

    if not impact.impacted_shipments:
        return result

    impacted_ids = {i.shipment_id for i in impact.impacted_shipments}
    impacted_shipments = [s for s in all_shipments if str(s["id"]) in impacted_ids]

    # ── 2. Risk scoring for affected shipments ───────────────────────────────
    risk_results: dict[str, shipment_risk.RiskResult] = {}
    ml_results: dict[str, predictive_risk.MLRiskResult] = {}
    combined_scores: dict[str, float] = {}

    for shipment in impacted_shipments:
        sid = str(shipment["id"])
        carrier = carriers_by_id.get(str(shipment.get("carrier_id") or ""), {})
        has_excursion = temperature_excursions.get(sid, False)

        det_result = shipment_risk.run(
            shipment=shipment,
            active_disruptions=[disruption],
            temperature_excursion=has_excursion,
            carrier=carrier,
        )
        ml_result = predictive_risk.run(
            shipment=shipment,
            active_disruptions=[disruption],
            carrier=carrier,
        )
        risk_results[sid] = det_result
        ml_results[sid] = ml_result

        if ml_result.ml_score is not None:
            combined = 0.6 * det_result.score + 0.4 * ml_result.ml_score
        else:
            combined = det_result.score
        combined_scores[sid] = round(combined, 4)

    # Sort by combined score descending — process highest-risk first
    sorted_shipments = sorted(
        impacted_shipments,
        key=lambda s: -combined_scores.get(str(s["id"]), 0),
    )

    # ── 3. Per-shipment recommendations ─────────────────────────────────────
    for shipment in sorted_shipments:
        sid = str(shipment["id"])
        risk = risk_results[sid]
        combined = combined_scores[sid]

        # Only generate recs for medium/high/critical
        if combined < 0.3:
            continue

        carrier = carriers_by_id.get(str(shipment.get("carrier_id") or ""), {})
        priority = _priority_from_score(combined)
        cargo_value = float(shipment.get("cargo_value_usd") or 0)
        disruption_severity = disruption.get("severity", "low")

        requires_approval = (
            cargo_value > approval_threshold_usd
            or disruption_severity == "critical"
        )

        # Build reasoning_factors from risk result
        reasoning_factors = [
            {
                "factor": f.name,
                "value": f.value,
                "contribution": f.contribution,
                "weight": f.weight,
            }
            for f in risk.factors
            if f.contribution > 0
        ]
        if ml_results[sid].ml_score is not None:
            for fc in ml_results[sid].top_features:
                reasoning_factors.append({
                    "factor": f"ml_{fc.feature_name}",
                    "value": fc.value,
                    "contribution": fc.importance,
                    "weight": 0.4,  # ML weight
                })

        # ── Reroute recommendation ──────────────────────────────────────────
        route_options = route_optimizer.run(
            shipment=shipment,
            active_disruptions=[disruption],
            available_routes=all_routes,
        )
        if route_options:
            best = route_options[0]
            tracking = shipment.get("tracking_number", sid)
            disruption_title = disruption.get("title", "active disruption")
            reason = (
                f"Shipment {tracking} is rerouted via {best.route_code} "
                f"({best.route_name}) because the current route is affected by "
                f"'{disruption_title}' (severity: {disruption_severity}, "
                f"combined risk: {combined:.2f}). "
                f"{best.route_code} has reliability {best.score:.2f} and "
                f"{'avoids' if best.avoids_all_disruptions else 'does not avoid'} "
                f"the disruption zone."
            )
            result.recommendations.append(
                RecommendationCandidate(
                    shipment_id=sid,
                    disruption_id=str(disruption["id"]),
                    type="reroute",
                    priority=priority,
                    title=f"Reroute {tracking} via {best.route_code}",
                    description=(
                        f"Alternative route {best.route_code} ({best.route_name}): "
                        f"est. {best.estimated_duration_hours:.0f}h, "
                        f"${best.estimated_cost_usd:,.0f}."
                    ),
                    reason=reason,
                    reasoning_factors=reasoning_factors,
                    alternative_route_id=best.route_id,
                    estimated_savings_usd=max(0.0, cargo_value * 0.005),
                    estimated_delay_reduction_hours=12.0,
                    requires_approval=requires_approval,
                )
            )

        # ── Carrier change recommendation ───────────────────────────────────
        carrier_options = carrier_recommender.run(
            shipment=shipment,
            current_carrier=carrier,
            all_carriers=all_carriers,
            active_disruptions=[disruption],
        )
        if carrier_options and combined >= 0.5:
            best_c = carrier_options[0]
            requires_carrier_approval = requires_approval or (
                best_c.cost_index > (float(carrier.get("cost_index") or 1.0) * 1.20)
            )
            tracking = shipment.get("tracking_number", sid)
            reason = (
                f"Carrier change for {tracking}: current carrier "
                f"{carrier.get('name', 'unknown')} is in the disruption zone of "
                f"'{disruption.get('title', 'disruption')}'. "
                f"{best_c.reason}"
            )
            result.recommendations.append(
                RecommendationCandidate(
                    shipment_id=sid,
                    disruption_id=str(disruption["id"]),
                    type="carrier_change",
                    priority=priority,
                    title=f"Switch {tracking} to {best_c.carrier_name}",
                    description=best_c.reason,
                    reason=reason,
                    reasoning_factors=reasoning_factors,
                    alternative_carrier_id=best_c.carrier_id,
                    estimated_savings_usd=max(0.0, cargo_value * 0.003),
                    estimated_delay_reduction_hours=8.0,
                    requires_approval=requires_carrier_approval,
                )
            )

        # ── Cold-chain expedite recommendation ──────────────────────────────
        has_excursion = temperature_excursions.get(sid, False)
        if shipment.get("temperature_required") and has_excursion:
            tracking = shipment.get("tracking_number", sid)
            reason = (
                f"Shipment {tracking} requires expedited delivery: "
                f"active temperature excursion detected on temperature-sensitive cargo "
                f"(cargo value: ${cargo_value:,.0f}). "
                f"Disruption '{disruption.get('title', '')}' increases excursion risk."
            )
            result.recommendations.append(
                RecommendationCandidate(
                    shipment_id=sid,
                    disruption_id=str(disruption["id"]),
                    type="expedite",
                    priority="critical",
                    title=f"Expedite {tracking} — cold-chain excursion",
                    description=(
                        "Temperature excursion detected. Immediate expedited "
                        "delivery required to preserve cargo integrity."
                    ),
                    reason=reason,
                    reasoning_factors=reasoning_factors,
                    estimated_savings_usd=cargo_value * 0.05,
                    estimated_delay_reduction_hours=0.0,
                    requires_approval=True,
                )
            )

    # ── 4. Fleet redeployment recommendations ───────────────────────────────
    needy_shipments = [
        s for s in all_shipments
        if s.get("status") in ("delayed", "at_risk")
        and str(s["id"]) in impacted_ids
    ]
    redeployments = fleet_intelligence.suggest_redeployments(all_fleet, needy_shipments)
    for r in redeployments:
        result.recommendations.append(
            RecommendationCandidate(
                shipment_id=r.target_shipment_id,
                disruption_id=str(disruption["id"]),
                type="fleet_redeploy",
                priority="medium",
                title=f"Redeploy idle vehicle to disrupted shipment",
                description=r.reason,
                reason=r.reason,
                reasoning_factors=[],
                requires_approval=True,  # fleet_redeploy always requires approval
            )
        )

    # ── 5. Cascading impact analysis ─────────────────────────────────────────
    cascade = cascade_impact.run(
        direct_shipment_ids=impacted_ids,
        all_shipments=all_shipments,
        fleet=all_fleet,
    )
    result.cascade_result = cascade

    if cascade.secondary_count > 0:
        result.recommendations.append(
            RecommendationCandidate(
                shipment_id=None,
                disruption_id=str(disruption["id"]),
                type="escalate",
                priority="high",
                title=f"Cascade alert: {cascade.secondary_count} secondary shipments at risk",
                description=cascade.explanation,
                reason=(
                    f"Cascading impact detected: '{disruption.get('title', 'disruption')}' "
                    f"directly affects {cascade.direct_count} shipments, with "
                    f"{cascade.secondary_count} secondary shipments at risk via fleet/carrier cascade. "
                    f"Total secondary cargo value: ${cascade.total_value_at_risk_usd:,.0f}."
                ),
                reasoning_factors=[],
                requires_approval=cascade.total_value_at_risk_usd > approval_threshold_usd,
            )
        )

    # ── 6. Business impact ───────────────────────────────────────────────────
    biz = business_impact.run(impacted_shipments)
    result.business_impact_result = biz

    return result


def _priority_from_score(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"
