"""Recommendation ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=True
    )
    disruption_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("disruptions.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # reroute/carrier_change/fleet_redeploy/hold/expedite/escalate
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium"
    )  # low/medium/high/critical
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)  # Required non-empty
    reasoning_factors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    alternative_route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id"), nullable=True
    )
    alternative_carrier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carriers.id"), nullable=True
    )
    estimated_savings_usd: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    estimated_delay_reduction_hours: Mapped[float | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending/approved/rejected/deferred/implemented
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    shipment: Mapped["Shipment | None"] = relationship("Shipment", back_populates="recommendations")  # noqa: F821
    disruption: Mapped["Disruption | None"] = relationship("Disruption", back_populates="recommendations")  # noqa: F821
    alternative_route: Mapped["Route | None"] = relationship("Route")  # noqa: F821
    alternative_carrier: Mapped["Carrier | None"] = relationship("Carrier")  # noqa: F821
