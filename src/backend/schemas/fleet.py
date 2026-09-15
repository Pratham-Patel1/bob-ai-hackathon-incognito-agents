"""Pydantic schemas for Fleet."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FleetBase(BaseModel):
    vehicle_id: str
    type: str
    carrier_id: uuid.UUID
    status: str = "active"
    current_location: str | None = None
    current_lat: float | None = None
    current_lng: float | None = None
    capacity_kg: float
    current_load_kg: float = 0.0
    utilization_pct: float = 0.0
    temperature_capable: bool = False
    temp_min_c: float | None = None
    temp_max_c: float | None = None


class FleetCreate(FleetBase):
    pass


class FleetRead(FleetBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    last_seen: datetime | None
    created_at: datetime
    updated_at: datetime
