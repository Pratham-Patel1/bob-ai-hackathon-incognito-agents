"""DecisionAudit ORM model — append-only audit trail."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class DecisionAudit(Base):
    """
    Immutable audit log. No UPDATE or DELETE operations are ever
    performed on this table — only INSERT (via write_audit utility).
    """

    __tablename__ = "decision_audit"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # shipment/disruption/recommendation/simulation
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # risk_calculated/rec_generated/rec_approved/rec_rejected/...
    actor: Mapped[str] = mapped_column(String(100), nullable=False)  # "system" or operator name
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # system/human
    previous_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
