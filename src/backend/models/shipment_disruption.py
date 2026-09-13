"""shipment_disruptions association table (many-to-many)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ShipmentDisruption(Base):
    """
    Association table representing the many-to-many relationship
    between Shipment and Disruption.

    Composite PK (shipment_id, disruption_id) ensures a shipment
    is linked to a given disruption at most once.
    """

    __tablename__ = "shipment_disruptions"

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    disruption_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disruptions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    impact_reason: Mapped[str] = mapped_column(
        String(200), nullable=False
    )  # geo_intersection / route_blocked / carrier_affected / combined
    distance_to_epicenter_km: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="disruption_links")  # noqa: F821
    disruption: Mapped["Disruption"] = relationship("Disruption", back_populates="shipment_links")  # noqa: F821
