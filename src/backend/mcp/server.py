"""
SupplyChainOS Model Context Protocol (MCP) Server.
Provides natural language and autonomous tool-calling capabilities for IBM Bob and AI copilots.
"""

import asyncio
from typing import Optional, Dict, Any

from .tools.shipment_tools import get_shipment_details, get_shipment_risk
from .tools.disruption_tools import list_active_disruptions, get_disruption_impact
from .tools.cold_chain_tools import check_cold_chain_status
from .tools.fleet_tools import get_fleet_recommendations
from .tools.route_tools import simulate_what_if_route


class SupplyChainOSMCPServer:
    """
    Standard MCP server wrapper exposing SupplyChainOS intelligence tools.
    """

    def __init__(self, name: str = "supplychainos-mcp-server"):
        self.name = name
        self.tools = {
            "get_shipment_details": get_shipment_details,
            "get_shipment_risk": get_shipment_risk,
            "list_active_disruptions": list_active_disruptions,
            "get_disruption_impact": get_disruption_impact,
            "check_cold_chain_status": check_cold_chain_status,
            "get_fleet_recommendations": get_fleet_recommendations,
            "simulate_what_if_route": simulate_what_if_route,
        }

    def list_tools(self) -> Dict[str, Any]:
        """Return registered tool manifests."""
        return {
            "server": self.name,
            "tools": [
                {
                    "name": name,
                    "description": func.__doc__.strip() if func.__doc__ else "",
                }
                for name, func in self.tools.items()
            ],
        }

    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Dispatch tool execution."""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}", "available_tools": list(self.tools.keys())}
        return await self.tools[tool_name](**kwargs)


# Global server instance
mcp_server = SupplyChainOSMCPServer()


if __name__ == "__main__":
    print(f"Starting {mcp_server.name} with {len(mcp_server.tools)} registered tools:")
    for t in mcp_server.list_tools()["tools"]:
        print(f" - {t['name']}")
