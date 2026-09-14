"""Pydantic schemas for Recommendation."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class RecommendationBase(BaseModel):
    shipment_id: uuid.UUID | None = None
    disruption_id: uuid.UUID | None = None
    type: str
    priority: str = "medium"
    title: str
    description: str | None = None
    reason: str
    reasoning_factors: list[Any] | None = None
    alternative_route_id: uuid.UUID | None = None
    alternative_carrier_id: uuid.UUID | None = None
    estimated_savings_usd: float | None = None
    estimated_delay_reduction_hours: float | None = None
    requires_approval: bool = False

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("reason must not be empty")
        return v


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationRead(RecommendationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ApprovalAction(BaseModel):
    actor: str
    notes: str | None = None
