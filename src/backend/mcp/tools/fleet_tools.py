"""
Fleet telematics and asset intelligence tools for Model Context Protocol (MCP).
"""

import os
from typing import Dict, Any, Optional
import httpx

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")


async def get_fleet_recommendations(
    min_capacity_tons: Optional[float] = None,
    is_refrigerated: Optional[bool] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Query fleet availability, location, and capacity utilization.
    Identifies idle, nearby, or refrigerated vehicles for shipment redeployment.

    Args:
        min_capacity_tons: Minimum required vehicle load capacity in tons.
        is_refrigerated: Whether refrigerated container (reefer) is required.
        status: Filter by vehicle status ('available', 'idle', 'in_transit').
    """
    url = f"{BACKEND_API_URL}/fleet"
    params = {}
    if min_capacity_tons is not None:
        params["min_capacity"] = min_capacity_tons
    if is_refrigerated is not None:
        params["is_refrigerated"] = is_refrigerated
    if status is not None:
        params["status"] = status

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                return {"fleet": response.json()}
            return {
                "error": "Failed to fetch fleet recommendations",
                "status_code": response.status_code,
                "detail": response.text,
            }
    except Exception as exc:
        return {
            "error": "Fleet service endpoint unreachable",
            "exception": str(exc),
        }
