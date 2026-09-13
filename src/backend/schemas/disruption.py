"""Pydantic schemas for Disruption."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DisruptionBase(BaseModel):
    type: str
    severity: str
    title: str
    description: str | None = None
    affected_region: str | None = None
    epicenter_lat: float
    epicenter_lng: float
    affected_radius_km: float
    affected_route_codes: list[str] = []
    status: str = "active"
    start_time: datetime
    estimated_end_time: datetime | None = None
    source: str = "manual"


class DisruptionCreate(DisruptionBase):
    pass


class DisruptionRead(DisruptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actual_end_time: datetime | None
    created_at: datetime
    updated_at: datetime
