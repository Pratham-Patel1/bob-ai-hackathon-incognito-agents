"""
RecommendationEngine — Phase 2F

The top-level synthesis layer that aggregates outputs from ALL other engines
and produces a single, actionable recommendation bundle for a disrupted shipment.

Architecture rules:
  - This engine does NOT call any other engine directly.
  - The router/service layer runs all sub-engines and collects their results.
  - Those results are passed here as plain dataclass instances OR plain dicts.
  - This engine produces one unified decision. NO DB access.

Input contract
--------------
All inputs are keyword-optional — engine results that haven't been computed
yet should simply be passed as None; the engine degrades gracefully.

shipment_context : dict
    Core shipment fields: id, tracking_number, status, cargo_type,
    cargo_value_usd, priority, temperature_required

risk_result : ShipmentRiskResult | None
    Output from ShipmentRiskEngine (Phase 2A-2)

predictive_result : PredictiveRiskResult | None
    Output from PredictiveRiskEngine (Phase 2B)

cold_chain_result : ColdChainAnalysisResult | None
    Output from ColdChainAnomalyEngine (Phase 2C)

fleet_result : FleetIntelligenceResult | None
    Output from FleetIntelligenceEngine (Phase 2C)

route_result : RouteOptimizationResult | None
    Output from RouteOptimizationEngine (Phase 2D)

carrier_result : CarrierRecommendationResult | None
    Output from CarrierRecommendationEngine (Phase 2D)

cascade_result : CascadeImpactResult | None
    Output from CascadingImpactEngine (Phase 2E)

twin_result : DigitalTwinResult | None
    Output from DigitalTwinEngine (Phase 2E)

business_result : BusinessImpactResult | None
    Output from BusinessImpactEngine (Phase 2E)

Output
------
RecommendationBundle dataclass:
    shipment_id             str
    tracking_number         str
    recommended_action      str   one of ACTION_* constants below
    urgency_level           str   "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    target_route_id         str | None
    target_carrier_id       str | None
    target_vehicle_id       str | None
    reasons                 list[str]
    business_impact         dict   (from BusinessImpactEngine or defaults)
    cascade_affected_count  int
    cold_chain_alert        bool
    confidence_score        float  0.0–1.0
    digital_twin_advice     str | None   "SWITCH" | "KEEP" | None
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Action constants
# ---------------------------------------------------------------------------

ACTION_REROUTE             = "REROUTE"           # switch to alternative route
ACTION_CARRIER_SWAP        = "CARRIER_SWAP"       # reassign to different carrier
ACTION_VEHICLE_REASSIGN    = "VEHICLE_REASSIGN"   # redeploy a different vehicle
ACTION_HOLD_AND_MONITOR    = "HOLD_AND_MONITOR"   # pause shipment and watch
ACTION_EXPEDITE            = "EXPEDITE"           # rush / prioritise current path
ACTION_COLD_CHAIN_ALERT    = "COLD_CHAIN_ALERT"   # temperature excursion action needed
ACTION_NO_ACTION           = "NO_ACTION"          # situation under control

# Urgency thresholds
_URGENCY_CRITICAL_SCORE = 75.0
_URGENCY_HIGH_SCORE     = 50.0
_URGENCY_MEDIUM_SCORE   = 25.0


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class RecommendationBundle:
    shipment_id: str
    tracking_number: str
    recommended_action: str
    urgency_level: str
    target_route_id: Optional[str]
    target_carrier_id: Optional[str]
    target_vehicle_id: Optional[str]
    reasons: List[str]
    business_impact: Dict[str, Any]
    cascade_affected_count: int
    cold_chain_alert: bool
    confidence_score: float
    digital_twin_advice: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _urgency_from_score(score: float) -> str:
    if score >= _URGENCY_CRITICAL_SCORE:
        return "CRITICAL"
    if score >= _URGENCY_HIGH_SCORE:
        return "HIGH"
    if score >= _URGENCY_MEDIUM_SCORE:
        return "MEDIUM"
    return "LOW"


def _get_attr(obj: Any, *keys: str, default: Any = None) -> Any:
    """
    Safely retrieve an attribute from a dataclass OR a dict key.
    Tries keys in order until one succeeds.
    """
    for key in keys:
        # dataclass attribute
        if hasattr(obj, key):
            val = getattr(obj, key)
            if val is not None:
                return val
        # dict key
        if isinstance(obj, dict) and key in obj and obj[key] is not None:
            return obj[key]
    return default


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def synthesize_recommendation(
    shipment_context: Dict[str, Any],
    risk_result: Any = None,
    predictive_result: Any = None,
    cold_chain_result: Any = None,
    fleet_result: Any = None,
    route_result: Any = None,
    carrier_result: Any = None,
    cascade_result: Any = None,
    twin_result: Any = None,
    business_result: Any = None,
) -> RecommendationBundle:
    """
    Synthesise all engine outputs into one unified recommendation.

    Parameters
    ----------
    shipment_context : dict
        Core shipment fields.
    *_result : engine dataclass or None
        Results from each sub-engine. Missing inputs gracefully degraded.

    Returns
    -------
    RecommendationBundle
    """
    shipment_id      = str(shipment_context.get("id") or "")
    tracking_number  = str(shipment_context.get("tracking_number") or shipment_id)
    priority         = str(shipment_context.get("priority") or "medium").lower()
    temp_required    = bool(shipment_context.get("temperature_required") or False)

    reasons: List[str] = []
    confidence_components: List[float] = []

    # ------------------------------------------------------------------
    # 1. Determine effective risk score
    # ------------------------------------------------------------------
    risk_score   = float(_get_attr(risk_result, "risk_score", default=0.0))
    risk_level   = str(_get_attr(risk_result, "risk_level", default="LOW"))
    ml_available = _get_attr(predictive_result, "available", default=False)
    delay_prob   = float(_get_attr(predictive_result, "delay_probability", default=0.0))
    delay_hours  = float(_get_attr(predictive_result, "predicted_delay_hours", default=0.0))

    if risk_score > 0:
        reasons.append(f"Shipment risk score: {risk_score:.1f}/100 ({risk_level})")
    if ml_available and delay_prob > 0.4:
        reasons.append(
            f"ML model predicts {delay_prob:.0%} probability of delay "
            f"(~{delay_hours:.0f}h extra)"
        )
        confidence_components.append(min(delay_prob * 1.2, 1.0))

    # ------------------------------------------------------------------
    # 2. Cold chain alert check
    # ------------------------------------------------------------------
    cold_chain_alert = False
    cold_chain_severity = str(_get_attr(cold_chain_result, "excursion_severity", default="NONE"))
    spoilage_risk = float(_get_attr(cold_chain_result, "spoilage_risk_percent", default=0.0))

    if cold_chain_severity in ("MAJOR", "CRITICAL"):
        cold_chain_alert = True
        reasons.append(
            f"Cold chain excursion: {cold_chain_severity} "
            f"(spoilage risk {spoilage_risk:.1f}%)"
        )
        confidence_components.append(0.80)
    elif cold_chain_severity == "MINOR":
        reasons.append(f"Cold chain MINOR excursion detected (spoilage risk {spoilage_risk:.1f}%)")

    # ------------------------------------------------------------------
    # 3. Cascade impact
    # ------------------------------------------------------------------
    cascade_count = int(_get_attr(cascade_result, "total_affected_count", default=0))
    if cascade_count > 0:
        reasons.append(
            f"Cascade impact: {cascade_count} downstream shipment(s)/vehicle(s) affected"
        )
        confidence_components.append(min(cascade_count / 5.0, 1.0))

    # ------------------------------------------------------------------
    # 4. Digital twin advice
    # ------------------------------------------------------------------
    twin_advice = _get_attr(twin_result, "recommendation", default=None)
    twin_confidence = float(_get_attr(twin_result, "confidence", default=0.0))
    if twin_advice == "SWITCH":
        reasons.append(
            f"Digital Twin simulation recommends SWITCH "
            f"(confidence {twin_confidence:.0%})"
        )
        confidence_components.append(twin_confidence)

    # ------------------------------------------------------------------
    # 5. Route recommendation
    # ------------------------------------------------------------------
    target_route_id: Optional[str] = None
    recommended_route = _get_attr(route_result, "recommended_route", default=None)
    if recommended_route is not None:
        target_route_id = str(_get_attr(recommended_route, "id", default=""))
        route_name      = str(_get_attr(recommended_route, "name", default=target_route_id))
        route_score     = float(_get_attr(recommended_route, "composite_score", default=0.0))
        reasons.append(
            f"Optimal reroute identified: '{route_name}' "
            f"(score {route_score:.1f})"
        )

    # ------------------------------------------------------------------
    # 6. Carrier recommendation
    # ------------------------------------------------------------------
    target_carrier_id: Optional[str] = None
    recommended_carrier = _get_attr(carrier_result, "recommended_carrier", default=None)
    if recommended_carrier is not None:
        target_carrier_id = str(_get_attr(recommended_carrier, "id", default=""))
        carrier_name      = str(_get_attr(recommended_carrier, "name", default=target_carrier_id))
        on_time           = float(_get_attr(recommended_carrier, "on_time_rate", default=0.0))
        reasons.append(
            f"Recommended carrier: '{carrier_name}' "
            f"({on_time:.0%} on-time rate)"
        )

    # ------------------------------------------------------------------
    # 7. Vehicle recommendation
    # ------------------------------------------------------------------
    target_vehicle_id: Optional[str] = None
    candidates = _get_attr(fleet_result, "redeployment_candidates", default=[])
    if candidates:
        best_vehicle = candidates[0]
        target_vehicle_id = str(_get_attr(best_vehicle, "id", default=""))
        veh_code          = str(_get_attr(best_vehicle, "vehicle_code", default=target_vehicle_id))
        veh_score         = float(_get_attr(best_vehicle, "suitability_score", default=0.0))
        reasons.append(
            f"Best vehicle for redeployment: '{veh_code}' "
            f"(suitability score {veh_score:.1f})"
        )

    # ------------------------------------------------------------------
    # 8. Business impact summary
    # ------------------------------------------------------------------
    business_impact: Dict[str, Any] = {}
    if business_result is not None:
        business_impact = {
            "cargo_value_at_risk_usd":    float(_get_attr(business_result, "cargo_value_at_risk_usd",    default=0.0)),
            "sla_penalty_usd":            float(_get_attr(business_result, "sla_penalty_usd",            default=0.0)),
            "extra_transport_cost_usd":   float(_get_attr(business_result, "extra_transport_cost_usd",   default=0.0)),
            "total_financial_exposure_usd": float(_get_attr(business_result, "total_financial_exposure_usd", default=0.0)),
            "risk_percentage":            float(_get_attr(business_result, "risk_percentage",            default=0.0)),
        }
        total_exposure = business_impact["total_financial_exposure_usd"]
        if total_exposure > 0:
            reasons.append(
                f"Financial exposure: ${total_exposure:,.0f} "
                f"({business_impact['risk_percentage']:.1f}% of cargo value)"
            )

    # ------------------------------------------------------------------
    # 9. Choose recommended_action (priority decision tree)
    # ------------------------------------------------------------------
    if cold_chain_alert:
        # Cold chain failure is always the highest priority action
        recommended_action = ACTION_COLD_CHAIN_ALERT

    elif risk_level in ("CRITICAL", "HIGH") and twin_advice == "SWITCH" and target_route_id:
        recommended_action = ACTION_REROUTE

    elif risk_level in ("CRITICAL", "HIGH") and target_carrier_id:
        recommended_action = ACTION_CARRIER_SWAP

    elif risk_level in ("CRITICAL", "HIGH") and target_vehicle_id:
        recommended_action = ACTION_VEHICLE_REASSIGN

    elif risk_level == "HIGH" and delay_prob > 0.60:
        recommended_action = ACTION_EXPEDITE

    elif risk_level in ("MEDIUM", "HIGH"):
        recommended_action = ACTION_HOLD_AND_MONITOR

    else:
        recommended_action = ACTION_NO_ACTION

    # ------------------------------------------------------------------
    # 10. Urgency and confidence
    # ------------------------------------------------------------------
    urgency_level = _urgency_from_score(risk_score)

    # Confidence = average of contributing signals; default 0.5 if nothing
    if confidence_components:
        confidence_score = round(
            min(sum(confidence_components) / len(confidence_components), 1.0), 3
        )
    else:
        # Base confidence from risk_level alone
        base_map = {"CRITICAL": 0.85, "HIGH": 0.70, "MEDIUM": 0.50, "LOW": 0.30}
        confidence_score = base_map.get(risk_level, 0.50)

    # ------------------------------------------------------------------
    # Fallback reason
    # ------------------------------------------------------------------
    if not reasons:
        reasons.append("All systems nominal — no action required")

    return RecommendationBundle(
        shipment_id=shipment_id,
        tracking_number=tracking_number,
        recommended_action=recommended_action,
        urgency_level=urgency_level,
        target_route_id=target_route_id or None,
        target_carrier_id=target_carrier_id or None,
        target_vehicle_id=target_vehicle_id or None,
        reasons=reasons,
        business_impact=business_impact,
        cascade_affected_count=cascade_count,
        cold_chain_alert=cold_chain_alert,
        confidence_score=confidence_score,
        digital_twin_advice=twin_advice,
    )
