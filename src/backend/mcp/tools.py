"""
SupplyChainOS — MCP Tools Implementation.
Implements the 9 standard SupplyChainOS MCP tools as thin adapters calling the FastAPI backend.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.mcp.client import BackendAPIClient
from backend.mcp.schemas import (
    AnalyzeDisruptionInput,
    GetShipmentRiskInput,
    CheckColdChainInput,
    GetFleetStatusInput,
    FindAlternativeRoutesInput,
    SimulateScenarioInput,
    GetRecommendationsInput,
    ApproveRecommendationInput,
    GetCascadeImpactInput,
)

logger = logging.getLogger(__name__)


# ── 1. analyze_disruption ──────────────────────────────────────────────────────
async def analyze_disruption_tool(args: dict[str, Any], client: BackendAPIClient) -> dict[str, Any]:
    """
    Analyze the blast radius, severity, and impacted shipments for a given disruption.
    """
    validated = AnalyzeDisruptionInput(**args)
    result = await client.get_disruption_impact(validated.disruption_id)
    return result if isinstance(result, dict) else {"result": result}


# ── 2. get_shipment_risk ───────────────────────────────────────────────────────
async def get_shipment_risk_tool(args: dict[str, Any], client: BackendAPIClient) -> dict[str, Any]:
    """
    Retrieve deterministic + predictive ML risk scores and top feature factors for a shipment.
    """
    validated = GetShipmentRiskInput(**args)
    result = await client.get_shipment_risk(validated.shipment_id)
    return result if isinstance(result, dict) else {"result": result}


# ── 3. check_cold_chain ────────────────────────────────────────────────────────
async def check_cold_chain_tool(args: dict[str, Any], client: BackendAPIClient) -> dict[str, Any]:
    """
    Inspect temperature telemetry, excursion duration, max deviation, and spoilage risk.
    """
    validated = CheckColdChainInput(**args)
    result = await client.get_cold_chain(validated.shipment_id)
    return result if isinstance(result, dict) else {"result": result}


# ── 4. get_fleet_status ────────────────────────────────────────────────────────
async def get_fleet_status_tool(args: dict[str, Any], client: BackendAPIClient) -> dict[str, Any]:
    """
    Retrieve fleet availability, idle/overloaded vehicle metrics, and redeployment suggestions.
    """
    validated = GetFleetStatusInput(**args)
    result = await client.get_fleet_status(validated.status)
    return result if isinstance(result, dict) else {"result": result}


# ── 5. find_alternative_routes ─────────────────────────────────────────────────
async def find_alternative_routes_tool(args: dict[str, Any], client: BackendAPIClient) -> dict[str, Any]:
    """
    Find alternative bypass routes for a given route origin/destination pair.
    """
    validated = FindAlternativeRoutesInput(**args)
    result = await client.find_alternative_routes(validated.route_id)
    if isinstance(result, list):
        return {"route_id": validated.route_id, "count": len(result), "alternative_routes": result}
    return result if isinstance(result, dict) else {"result": result}


# ── 6. simulate_scenario ───────────────────────────────────────────────────────
async def simulate_scenario_tool(args: dict[str, Any], client: BackendAPIClient) -> dict[str, Any]:
    """
    Run an in-memory Digital Twin what-if scenario simulation without mutating operational data.
    """
    validated = SimulateScenarioInput(**args)
    result = await client.simulate_scenario(validated.model_dump())
    return result if isinstance(result, dict) else {"result": result}


# ── 7. get_recommendations ─────────────────────────────────────────────────────
async def get_recommendations_tool(args: dict[str, Any], client: BackendAPIClient) -> dict[str, Any]:
    """
    Retrieve multi-objective recommendations (reroutes, carrier swaps, expedites, fleet redeployments).
    """
    validated = GetRecommendationsInput(**args)
    result = await client.get_recommendations(
        status=validated.status,
        rec_type=validated.type,
        priority=validated.priority,
    )
    if isinstance(result, list):
        return {"count": len(result), "recommendations": result}
    return result if isinstance(result, dict) else {"result": result}


# ── 8. approve_recommendation ──────────────────────────────────────────────────
async def approve_recommendation_tool(args: dict[str, Any], client: BackendAPIClient) -> dict[str, Any]:
    """
    Execute human-in-the-loop approval on a pending recommendation via the approval state machine.
    """
    validated = ApproveRecommendationInput(**args)
    result = await client.approve_recommendation(
        recommendation_id=validated.recommendation_id,
        actor=validated.actor,
        notes=validated.notes,
    )
    return result if isinstance(result, dict) else {"result": result}


# ── 9. get_cascade_impact ──────────────────────────────────────────────────────
async def get_cascade_impact_tool(args: dict[str, Any], client: BackendAPIClient) -> dict[str, Any]:
    """
    Calculate 2nd-order downstream ripple effects on connecting fleets and carriers.
    """
    validated = GetCascadeImpactInput(**args)
    result = await client.get_cascade_impact(validated.disruption_id)
    return result if isinstance(result, dict) else {"result": result}


# ── Tool Registry Mapping ──────────────────────────────────────────────────────
TOOL_DISPATCH_TABLE = {
    "analyze_disruption": analyze_disruption_tool,
    "get_shipment_risk": get_shipment_risk_tool,
    "check_cold_chain": check_cold_chain_tool,
    "get_fleet_status": get_fleet_status_tool,
    "find_alternative_routes": find_alternative_routes_tool,
    "simulate_scenario": simulate_scenario_tool,
    "get_recommendations": get_recommendations_tool,
    "approve_recommendation": approve_recommendation_tool,
    "get_cascade_impact": get_cascade_impact_tool,
}
