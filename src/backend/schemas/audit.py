"""Pydantic schemas for DecisionAudit."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    actor: str
    actor_type: str
    previous_state: dict[str, Any] | None
    new_state: dict[str, Any] | None
    reasoning: str | None
    extra_metadata: dict[str, Any] | None
    created_at: datetime
