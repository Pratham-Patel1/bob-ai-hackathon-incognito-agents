"""Pydantic schemas for simulation."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SimulationScenario(BaseModel):
    """What-if scenario parameters."""

    disruption_type: str = "weather"
    disruption_severity: str = "high"
    epicenter_lat: float
    epicenter_lng: float
    affected_radius_km: float = 200.0
    affected_route_codes: list[str] = []
    title: str = "What-if Simulation"
    description: str | None = None
    shipment_ids: list[str] | None = None  # None = all active shipments


class SimulationResult(BaseModel):
    """Result returned by the digital twin engine."""

    scenario_summary: dict[str, Any]
    affected_shipment_count: int
    risk_scores: list[dict[str, Any]]
    cascade_analysis: dict[str, Any] | None = None
    business_impact: dict[str, Any] | None = None
    top_recommendations: list[dict[str, Any]] = []
