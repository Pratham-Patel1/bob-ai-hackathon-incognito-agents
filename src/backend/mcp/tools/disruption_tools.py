"""
Disruption intelligence and impact tools for Model Context Protocol (MCP).
"""

import os
from typing import Dict, Any, Optional
import httpx

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")


async def list_active_disruptions(severity: Optional[str] = None) -> Dict[str, Any]:
    """
    List all active supply chain disruptions (weather, strike, road closures, etc.).

    Args:
        severity: Optional filter by severity ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL').
    """
    url = f"{BACKEND_API_URL}/disruptions"
    params = {"severity": severity} if severity else {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                return {"disruptions": response.json()}
            return {"error": "Failed to fetch disruptions", "status_code": response.status_code}
    except Exception as exc:
        return {"error": "Connectivity failure", "exception": str(exc)}


async def get_disruption_impact(disruption_id: str) -> Dict[str, Any]:
    """
    Execute DisruptionImpactEngine to evaluate all shipments affected by a given disruption,
    including impact scores, levels, estimated delay hours, and explainable factors.

    Args:
        disruption_id: UUID of the disruption event.
    """
    url = f"{BACKEND_API_URL}/disruptions/{disruption_id}/impact"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            return {
                "error": f"Failed to calculate impact for disruption {disruption_id}",
                "status_code": response.status_code,
                "detail": response.text,
            }
    except Exception as exc:
        return {
            "error": "Disruption impact endpoint unreachable",
            "disruption_id": disruption_id,
            "exception": str(exc),
        }
