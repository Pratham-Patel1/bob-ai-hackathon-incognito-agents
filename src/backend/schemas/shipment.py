"""Pydantic schemas for Shipment."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ShipmentBase(BaseModel):
    tracking_number: str
    origin: str
    destination: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    current_location: str | None = None
    current_lat: float | None = None
    current_lng: float | None = None
    carrier_id: uuid.UUID
    route_id: uuid.UUID
    fleet_id: uuid.UUID | None = None
    status: str = "in_transit"
    scheduled_departure: datetime
    scheduled_arrival: datetime
    estimated_arrival: datetime | None = None
    cargo_type: str = "general"
    cargo_value_usd: float
    weight_kg: float
    temperature_required: bool = False
    temp_min_c: float | None = None
    temp_max_c: float | None = None


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentRead(ShipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actual_arrival: datetime | None
    risk_score: float
    risk_level: str
    ml_risk_score: float | None
    combined_risk_score: float | None
    created_at: datetime
    updated_at: datetime
