"""
SupplyChainOS — Model Context Protocol (MCP) Server.
Provides standardized JSON-RPC 2.0 tool endpoints for LLM Copilots (IBM Bob Copilot / watsonx.ai).
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any, Optional

from pydantic import ValidationError

from backend.mcp.client import BackendAPIClient, DEFAULT_API_BASE
from backend.mcp.security import (
    ALLOWED_TOOLS,
    MCPSecurityError,
    validate_tool_allowed,
    sanitize_input_strings,
    mask_sensitive_error,
)
from backend.mcp.tools import TOOL_DISPATCH_TABLE

logger = logging.getLogger(__name__)

# Standard MCP Tool Definitions with complete JSON Schemas
MCP_TOOL_DEFINITIONS = [
    {
        "name": "analyze_disruption",
        "description": "Evaluate the geographic impact and blast radius of an active disruption on in-transit shipments.",
        "inputSchema": {
            "type": "object",
            "required": ["disruption_id"],
            "properties": {
                "disruption_id": {"type": "string", "description": "Unique UUID of the disruption"},
            },
        },
    },
    {
        "name": "get_shipment_risk",
        "description": "Retrieve multi-factor deterministic risk scores, machine learning delay probability, and top risk factors for a specific shipment.",
        "inputSchema": {
            "type": "object",
            "required": ["shipment_id"],
            "properties": {
                "shipment_id": {"type": "string", "description": "Unique UUID of the shipment"},
            },
        },
    },
    {
        "name": "check_cold_chain",
        "description": "Inspect sensor telematics, detect temperature excursions, and evaluate spoilage risk on cold-chain sensitive shipments.",
        "inputSchema": {
            "type": "object",
            "required": ["shipment_id"],
            "properties": {
                "shipment_id": {"type": "string", "description": "Unique UUID of the shipment"},
            },
        },
    },
    {
        "name": "get_fleet_status",
        "description": "Query fleet asset utilization, idle and overloaded vehicle telemetry, and redeployment suggestions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["all", "idle", "overloaded", "available"],
                    "description": "Filter by vehicle operational status (default: all)",
                },
            },
        },
    },
    {
        "name": "find_alternative_routes",
        "description": "Find and rank alternative bypass routes for a given route origin/destination corridor.",
        "inputSchema": {
            "type": "object",
            "required": ["route_id"],
            "properties": {
                "route_id": {"type": "string", "description": "Unique UUID of the route"},
            },
        },
    },
    {
        "name": "simulate_scenario",
        "description": "Run an in-memory Digital Twin what-if scenario simulation for hypothetical disruptions without altering production data.",
        "inputSchema": {
            "type": "object",
            "required": ["title", "disruption_type", "disruption_severity", "epicenter_lat", "epicenter_lng", "affected_radius_km"],
            "properties": {
                "title": {"type": "string", "description": "Scenario title"},
                "disruption_type": {"type": "string", "description": "Type of disruption (e.g. severe_weather, infrastructure, cyclone, port_congestion)"},
                "disruption_severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "epicenter_lat": {"type": "number", "description": "Latitude (-90 to +90)"},
                "epicenter_lng": {"type": "number", "description": "Longitude (-180 to +180)"},
                "affected_radius_km": {"type": "number", "description": "Blast radius in kilometers (1-10000)"},
                "affected_route_codes": {"type": "array", "items": {"type": "string"}},
                "shipment_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "get_recommendations",
        "description": "Query AI-orchestrated operational recommendations (reroutes, carrier swaps, expedites, fleet redeployments).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pending", "approved", "rejected", "deferred", "implemented"]},
                "type": {"type": "string", "description": "Filter by recommendation type"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            },
        },
    },
    {
        "name": "approve_recommendation",
        "description": "Execute human-in-the-loop approval on a pending recommendation with mandatory actor attribution and audit logging.",
        "inputSchema": {
            "type": "object",
            "required": ["recommendation_id", "actor"],
            "properties": {
                "recommendation_id": {"type": "string", "description": "Unique UUID of the recommendation"},
                "actor": {"type": "string", "description": "Name or ID of the human approver"},
                "notes": {"type": "string", "description": "Approval justification notes"},
            },
        },
    },
    {
        "name": "get_cascade_impact",
        "description": "Calculate secondary cascade ripple effects across shared fleets and connecting carrier routes for a disruption.",
        "inputSchema": {
            "type": "object",
            "required": ["disruption_id"],
            "properties": {
                "disruption_id": {"type": "string", "description": "Unique UUID of the disruption"},
            },
        },
    },
]


class SupplyChainOSMCPServer:
    """Standard Model Context Protocol Server for SupplyChainOS."""

    def __init__(self, api_client: Optional[BackendAPIClient] = None, api_base_url: str = DEFAULT_API_BASE):
        self.client = api_client or BackendAPIClient(base_url=api_base_url)
        self.tools = {defn["name"]: defn for defn in MCP_TOOL_DEFINITIONS}

    def list_tools(self) -> list[dict[str, Any]]:
        """Return list of authorized tool declarations."""
        return MCP_TOOL_DEFINITIONS

    async def call_tool(self, name: str, arguments: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Validate and dispatch a tool call."""
        args = arguments or {}

        # 1. Security check: Tool allowlist
        validate_tool_allowed(name)

        # 2. Security check: Parameter sanitization
        sanitize_input_strings(args)

        # 3. Retrieve handler
        handler = TOOL_DISPATCH_TABLE.get(name)
        if not handler:
            raise MCPSecurityError(f"Handler for tool '{name}' not found.")

        # 4. Execute tool
        try:
            result = await handler(args, self.client)
            return {
                "tool": name,
                "status": "success",
                "content": result,
            }
        except ValidationError as ve:
            logger.warning("Input validation failed for MCP tool '%s': %s", name, ve)
            return {
                "tool": name,
                "status": "error",
                "error_type": "ValidationError",
                "message": f"Invalid arguments for {name}: {str(ve)}",
            }
        except MCPSecurityError as se:
            logger.warning("Security policy violation in MCP tool '%s': %s", name, se)
            return {
                "tool": name,
                "status": "error",
                "error_type": "SecurityError",
                "message": se.message,
            }
        except Exception as exc:
            logger.error("Unexpected error executing MCP tool '%s': %s", name, exc, exc_info=True)
            return {
                "tool": name,
                "status": "error",
                "error_type": "ExecutionError",
                "message": mask_sensitive_error(exc),
            }

    async def handle_jsonrpc(self, request: dict[str, Any]) -> dict[str, Any]:
        """Standard JSON-RPC 2.0 protocol handler."""
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if not method or request.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Invalid Request: expected jsonrpc='2.0'"},
            }

        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "supplychainos-mcp-server", "version": "1.0.0"},
                        "capabilities": {"tools": {}},
                    },
                }
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": self.list_tools()},
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                tool_res = await self.call_tool(tool_name, tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": tool_res,
                }
            elif method == "ping":
                return {"jsonrpc": "2.0", "id": req_id, "result": "pong"}
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: '{method}'"},
                }
        except Exception as exc:
            logger.error("JSON-RPC error handling %s: %s", method, exc, exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": mask_sensitive_error(exc)},
            }
