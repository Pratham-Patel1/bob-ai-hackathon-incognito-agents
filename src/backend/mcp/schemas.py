"""
SupplyChainOS — Model Context Protocol (MCP) input schemas.
Enforces strict input validation, range checks, and type safety for all 9 MCP tools.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def validate_uuid_str(val: str, field_name: str) -> str:
    if not val or not isinstance(val, str) or not UUID_REGEX.match(val.strip()):
        raise ValueError(f"Invalid {field_name}: must be a valid 36-character UUID string")
    return val.strip()


class AnalyzeDisruptionInput(BaseModel):
    disruption_id: str = Field(..., description="Unique UUID of the disruption to analyze")

    @field_validator("disruption_id")
    @classmethod
    def check_uuid(cls, v: str) -> str:
        return validate_uuid_str(v, "disruption_id")


class GetShipmentRiskInput(BaseModel):
    shipment_id: str = Field(..., description="Unique UUID of the shipment")

    @field_validator("shipment_id")
    @classmethod
    def check_uuid(cls, v: str) -> str:
        return validate_uuid_str(v, "shipment_id")


class CheckColdChainInput(BaseModel):
    shipment_id: str = Field(..., description="Unique UUID of the temperature-sensitive shipment")

    @field_validator("shipment_id")
    @classmethod
    def check_uuid(cls, v: str) -> str:
        return validate_uuid_str(v, "shipment_id")


class GetFleetStatusInput(BaseModel):
    status: Literal["all", "idle", "overloaded", "available"] | None = Field(
        default="all",
        description="Filter fleet by operational status (all, idle, overloaded, available)"
    )


class FindAlternativeRoutesInput(BaseModel):
    route_id: str = Field(..., description="Unique UUID of the active or disrupted route")

    @field_validator("route_id")
    @classmethod
    def check_uuid(cls, v: str) -> str:
        return validate_uuid_str(v, "route_id")


class SimulateScenarioInput(BaseModel):
    title: str = Field(..., min_length=3, max_length=150, description="Title of the hypothetical scenario")
    disruption_type: str = Field(
        ...,
        description="Type of disruption (severe_weather, infrastructure, cyclone, port_congestion, geopolitical, customs_delay, equipment_failure, labor_strike)"
    )
    disruption_severity: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Severity level of the hypothetical disruption"
    )
    epicenter_lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude of the disruption epicenter (-90 to +90)")
    epicenter_lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude of the disruption epicenter (-180 to +180)")
    affected_radius_km: float = Field(..., gt=0.0, le=10000.0, description="Geographic blast radius in kilometers (0 to 10,000)")
    affected_route_codes: list[str] = Field(default_factory=list, description="Optional list of route codes directly blocked (e.g. ['RT-01'])")
    shipment_ids: list[str] = Field(default_factory=list, description="Optional list of specific shipment UUIDs to simulate")

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("title cannot be empty or whitespace only")
        return s


class GetRecommendationsInput(BaseModel):
    status: Literal["pending", "approved", "rejected", "deferred", "implemented"] | None = Field(
        default=None,
        description="Filter recommendations by status (pending, approved, rejected, deferred, implemented)"
    )
    type: str | None = Field(default=None, description="Filter by recommendation type (reroute, carrier_change, expedite, fleet_redeploy, escalate)")
    priority: Literal["low", "medium", "high", "critical"] | None = Field(
        default=None,
        description="Filter by priority (low, medium, high, critical)"
    )


class ApproveRecommendationInput(BaseModel):
    recommendation_id: str = Field(..., description="Unique UUID of the recommendation to approve")
    actor: str = Field(..., min_length=2, max_length=100, description="Name or ID of the human approver / sign-off officer")
    notes: str | None = Field(default=None, max_length=1000, description="Audit justification or operational sign-off notes")

    @field_validator("recommendation_id")
    @classmethod
    def check_uuid(cls, v: str) -> str:
        return validate_uuid_str(v, "recommendation_id")

    @field_validator("actor")
    @classmethod
    def check_actor(cls, v: str) -> str:
        s = v.strip()
        if not s or s.lower() in ("anonymous", "unknown", "none", "null"):
            raise ValueError("actor must be an identified human dispatcher or operations officer")
        return s


class GetCascadeImpactInput(BaseModel):
    disruption_id: str = Field(..., description="Unique UUID of the disruption to compute cascade impact for")

    @field_validator("disruption_id")
    @classmethod
    def check_uuid(cls, v: str) -> str:
        return validate_uuid_str(v, "disruption_id")
