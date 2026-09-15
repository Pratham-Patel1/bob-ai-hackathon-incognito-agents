"""
SupplyChainOS — MCP Backend API Client Adapter.
Forwards MCP tool invocations to the verified FastAPI REST API endpoints.
Never accesses PostgreSQL directly.
"""
from __future__ import annotations

import os
import logging
from typing import Any, Optional
import httpx

from backend.mcp.security import mask_sensitive_error

logger = logging.getLogger(__name__)

DEFAULT_API_BASE = os.getenv("SUPPLYCHAINOS_API_URL", "http://localhost:8000/api/v1")


class BackendAPIClient:
    """HTTP client adapter connecting MCP tools to the FastAPI backend layer."""

    def __init__(
        self,
        base_url: str = DEFAULT_API_BASE,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout_seconds: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self._custom_client = http_client
        self.timeout = timeout_seconds

    def _get_client(self) -> httpx.AsyncClient:
        if self._custom_client is not None:
            return self._custom_client
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any] | list[Any]:
        """Execute safe HTTP request to FastAPI backend with error masking."""
        url_path = path if path.startswith("/") else f"/{path}"
        req_headers = {"Accept": "application/json", **(headers or {})}

        client = self._get_client()
        try:
            # If client is managed internally (not custom), use async context manager
            if self._custom_client is None:
                async with client as c:
                    resp = await c.request(
                        method=method,
                        url=url_path,
                        params=params,
                        json=json_data,
                        headers=req_headers,
                    )
            else:
                resp = await client.request(
                    method=method,
                    url=url_path,
                    params=params,
                    json=json_data,
                    headers=req_headers,
                )

            if resp.status_code == 404:
                return {"error": "Resource not found", "status_code": 404, "detail": resp.json().get("detail", "Not Found")}
            elif resp.status_code == 409:
                return {"error": "Conflict in state machine", "status_code": 409, "detail": resp.json().get("detail", "Conflict")}
            elif resp.status_code >= 400:
                detail = resp.json().get("detail", f"HTTP {resp.status_code} Error") if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                return {"error": "Backend API request failed", "status_code": resp.status_code, "detail": detail}

            return resp.json()
        except httpx.RequestError as exc:
            logger.error("HTTP error connecting to backend API (%s %s): %s", method, url_path, exc)
            return {
                "error": "Backend connection failure",
                "status_code": 503,
                "detail": f"Failed to reach SupplyChainOS backend at {self.base_url}. Error: {mask_sensitive_error(exc)}",
            }

    # ── 1. Disruption Impact ───────────────────────────────────────────────────
    async def get_disruption_impact(self, disruption_id: str) -> Any:
        return await self._request("GET", f"/disruptions/{disruption_id}/impact")

    # ── 2. Shipment Risk ──────────────────────────────────────────────────────
    async def get_shipment_risk(self, shipment_id: str) -> Any:
        return await self._request("GET", f"/shipments/{shipment_id}/risk")

    # ── 3. Cold Chain Telemetry ───────────────────────────────────────────────
    async def get_cold_chain(self, shipment_id: str) -> Any:
        return await self._request("GET", f"/shipments/{shipment_id}/temperature")

    # ── 4. Fleet Status & Redeployment ────────────────────────────────────────
    async def get_fleet_status(self, status: Optional[str] = "all") -> Any:
        if status == "idle":
            return await self._request("GET", "/fleet/idle")
        elif status == "overloaded":
            return await self._request("GET", "/fleet/overloaded")
        elif status == "available":
            return await self._request("GET", "/fleet", params={"status": "available"})
        # Default: full fleet analysis with redeployment suggestions
        return await self._request("GET", "/fleet/redeployment-suggestions")

    # ── 5. Alternative Routes ─────────────────────────────────────────────────
    async def find_alternative_routes(self, route_id: str) -> Any:
        return await self._request("GET", f"/routes/{route_id}/alternatives")

    # ── 6. Digital Twin Scenario Simulation ───────────────────────────────────
    async def simulate_scenario(self, scenario: dict[str, Any]) -> Any:
        return await self._request("POST", "/simulation/run", json_data=scenario)

    # ── 7. Recommendations ────────────────────────────────────────────────────
    async def get_recommendations(
        self,
        status: Optional[str] = None,
        rec_type: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Any:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if rec_type:
            params["type"] = rec_type
        if priority:
            params["priority"] = priority
        return await self._request("GET", "/recommendations", params=params)

    # ── 8. Approve Recommendation ─────────────────────────────────────────────
    async def approve_recommendation(
        self,
        recommendation_id: str,
        actor: str,
        notes: Optional[str] = None,
    ) -> Any:
        payload = {"actor": actor, "notes": notes or f"Approved via MCP by {actor}"}
        return await self._request("POST", f"/recommendations/{recommendation_id}/approve", json_data=payload)

    # ── 9. Cascade Impact ─────────────────────────────────────────────────────
    async def get_cascade_impact(self, disruption_id: str) -> Any:
        return await self._request("GET", f"/disruptions/{disruption_id}/cascade")
