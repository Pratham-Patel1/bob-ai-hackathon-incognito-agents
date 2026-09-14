"""Disruption ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Disruption(Base):
    __tablename__ = "disruptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # weather/strike/geopolitical/infrastructure/other
    severity: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # low/medium/high/critical
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    epicenter_lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    epicenter_lng: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    affected_radius_km: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    affected_route_codes: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active/monitoring/resolved
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estimated_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual"
    )  # manual/simulated/api
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    shipment_links: Mapped[list["ShipmentDisruption"]] = relationship(  # noqa: F821
        "ShipmentDisruption", back_populates="disruption", cascade="all, delete-orphan"
    )
    affected_shipments: Mapped[list["Shipment"]] = relationship(  # noqa: F821
        "Shipment",
        secondary="shipment_disruptions",
        back_populates="disruptions",
        viewonly=True,
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(  # noqa: F821
        "Recommendation", back_populates="disruption"
    )
