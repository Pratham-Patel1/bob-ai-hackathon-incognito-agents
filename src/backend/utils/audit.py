"""Audit utility — shared write_audit function for all engines and routers."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.decision_audit import DecisionAudit

logger = logging.getLogger(__name__)


async def write_audit(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    actor: str,
    actor_type: str,
    reasoning: str | None = None,
    previous_state: dict[str, Any] | None = None,
    new_state: dict[str, Any] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> DecisionAudit:
    """
    Append an immutable audit record.

    Args:
        session:        Active async DB session (caller manages commit).
        entity_type:    "shipment" | "disruption" | "recommendation" | "simulation"
        entity_id:      UUID of the entity being audited.
        action:         e.g. "risk_calculated", "rec_approved", "simulation_run"
        actor:          "system" or operator name/ID.
        actor_type:     "system" | "human"
        reasoning:      Human-readable explanation of why this action occurred.
        previous_state: Snapshot of entity state before the change (nullable).
        new_state:      Snapshot of entity state after the change.
        extra_metadata: Engine outputs, model scores, etc.

    Returns:
        The persisted DecisionAudit row.
    """
    record = DecisionAudit(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        actor_type=actor_type,
        reasoning=reasoning,
        previous_state=previous_state,
        new_state=new_state,
        extra_metadata=extra_metadata,
    )
    session.add(record)
    # Caller is responsible for commit — do not commit here
    logger.debug(
        "audit: entity_type=%s entity_id=%s action=%s actor=%s",
        entity_type,
        entity_id,
        action,
        actor,
    )
    return record
