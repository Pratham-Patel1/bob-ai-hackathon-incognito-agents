"""
Route optimization and Digital Twin simulation tools for Model Context Protocol (MCP).
"""

import os
from typing import Dict, Any, Optional
import httpx

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")


async def simulate_what_if_route(
    shipment_id: str,
    candidate_route_id: str,
    candidate_carrier_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run in-memory Digital Twin simulation comparing baseline vs alternative reroute
    and carrier options. Calculates delta in risk, delay hours, and operational costs
    without modifying database state.

    Args:
        shipment_id: UUID of the shipment to simulate.
        candidate_route_id: UUID of the proposed alternative route.
        candidate_carrier_id: Optional UUID of the proposed carrier.
    """
    url = f"{BACKEND_API_URL}/simulations/route"
    payload = {
        "shipment_id": shipment_id,
        "candidate_route_id": candidate_route_id,
    }
    if candidate_carrier_id:
        payload["candidate_carrier_id"] = candidate_carrier_id

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
            return {
                "error": "Digital Twin simulation failed",
                "status_code": response.status_code,
                "detail": response.text,
            }
    except Exception as exc:
        return {
            "error": "Simulation service endpoint unreachable",
            "shipment_id": shipment_id,
            "exception": str(exc),
        }
