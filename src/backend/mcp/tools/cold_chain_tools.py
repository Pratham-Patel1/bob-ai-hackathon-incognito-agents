"""
Cold-chain IoT telemetry and temperature excursion analysis tools for MCP.
"""

import os
from typing import Dict, Any
import httpx

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")


async def check_cold_chain_status(shipment_id: str) -> Dict[str, Any]:
    """
    Query IoT sensor history for a temperature-sensitive shipment and run ColdChainAnomalyEngine
    to detect excursions, classify severity (MINOR, MAJOR, CRITICAL), and estimate spoilage risk.

    Args:
        shipment_id: UUID or tracking ID of the perishable/cold-chain shipment.
    """
    url = f"{BACKEND_API_URL}/shipments/{shipment_id}/cold-chain"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            return {
                "error": f"Failed to retrieve cold chain status for shipment {shipment_id}",
                "status_code": response.status_code,
                "detail": response.text,
            }
    except Exception as exc:
        return {
            "error": "Cold-chain engine endpoint unreachable",
            "shipment_id": shipment_id,
            "exception": str(exc),
        }
