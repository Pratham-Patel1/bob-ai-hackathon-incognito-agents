"""Pydantic schemas for Route."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RouteBase(BaseModel):
    code: str
    name: str
    origin: str
    destination: str
    waypoints: list[dict[str, Any]] | None = None
    mode: str
    distance_km: float
    typical_duration_hours: float
    cost_per_kg_usd: float
    reliability_score: float
    active: bool = True


class RouteCreate(RouteBase):
    pass


class RouteRead(RouteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
