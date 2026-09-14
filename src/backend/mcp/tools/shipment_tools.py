"""
Shipment intelligence tools for Model Context Protocol (MCP).
"""

import os
from typing import Dict, Any, Optional
import httpx

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")


async def get_shipment_details(shipment_id: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive details for a specific shipment including cargo type,
    value, priority, deadline, carrier, and temperature sensitivity.

    Args:
        shipment_id: Unique identifier or tracking number of the shipment.
    """
    url = f"{BACKEND_API_URL}/shipments/{shipment_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            return {
                "error": f"Failed to retrieve shipment {shipment_id}",
                "status_code": response.status_code,
                "detail": response.text,
            }
    except Exception as exc:
        return {
            "error": "Network/Backend connectivity failure",
            "shipment_id": shipment_id,
            "exception": str(exc),
        }


async def get_shipment_risk(shipment_id: str) -> Dict[str, Any]:
    """
    Retrieve computed multi-factor operational and predictive ML risk score for a shipment.

    Args:
        shipment_id: Unique identifier of the shipment.
    """
    url = f"{BACKEND_API_URL}/shipments/{shipment_id}/risk"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            return {
                "error": f"Failed to calculate risk for shipment {shipment_id}",
                "status_code": response.status_code,
                "detail": response.text,
            }
    except Exception as exc:
        return {
            "error": "Risk engine endpoint unreachable",
            "shipment_id": shipment_id,
            "exception": str(exc),
        }
