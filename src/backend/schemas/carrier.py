"""Pydantic schemas for Carrier."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CarrierBase(BaseModel):
    name: str
    code: str
    type: str
    reliability_score: float
    cost_index: float
    coverage_regions: list[str] = []
    active: bool = True
    contact_name: str | None = None
    contact_email: str | None = None


class CarrierCreate(CarrierBase):
    pass


class CarrierRead(CarrierBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
