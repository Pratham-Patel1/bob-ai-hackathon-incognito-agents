"""
SupplyChainOS — Model Context Protocol (MCP) Package.
Integrates Bob Copilot and watsonx.ai with SupplyChainOS pure-Python engines and FastAPI backend.
"""
from __future__ import annotations

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
from backend.mcp.security import (
    ALLOWED_TOOLS,
    MCPSecurityError,
    validate_tool_allowed,
)
from backend.mcp.tools import (
    analyze_disruption_tool,
    get_shipment_risk_tool,
    check_cold_chain_tool,
    get_fleet_status_tool,
    find_alternative_routes_tool,
    simulate_scenario_tool,
    get_recommendations_tool,
    approve_recommendation_tool,
    get_cascade_impact_tool,
)
from backend.mcp.server import SupplyChainOSMCPServer, MCP_TOOL_DEFINITIONS

__all__ = [
    "SupplyChainOSMCPServer",
    "BackendAPIClient",
    "MCP_TOOL_DEFINITIONS",
    "ALLOWED_TOOLS",
    "MCPSecurityError",
    "validate_tool_allowed",
    "AnalyzeDisruptionInput",
    "GetShipmentRiskInput",
    "CheckColdChainInput",
    "GetFleetStatusInput",
    "FindAlternativeRoutesInput",
    "SimulateScenarioInput",
    "GetRecommendationsInput",
    "ApproveRecommendationInput",
    "GetCascadeImpactInput",
    "analyze_disruption_tool",
    "get_shipment_risk_tool",
    "check_cold_chain_tool",
    "get_fleet_status_tool",
    "find_alternative_routes_tool",
    "simulate_scenario_tool",
    "get_recommendations_tool",
    "approve_recommendation_tool",
    "get_cascade_impact_tool",
]
