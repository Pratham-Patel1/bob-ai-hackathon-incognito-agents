"""Shipment ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tracking_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    origin: Mapped[str] = mapped_column(String(100), nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    origin_lng: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    destination_lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    destination_lng: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    current_location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    current_lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    carrier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carriers.id"), nullable=False
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id"), nullable=False
    )
    fleet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fleet.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="in_transit"
    )  # in_transit/delayed/delivered/at_risk/held
    scheduled_departure: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_arrival: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estimated_arrival: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_arrival: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cargo_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general"
    )  # general/temperature_sensitive/hazmat/fragile
    cargo_value_usd: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    temperature_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    temp_min_c: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    temp_max_c: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    risk_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False, default="low")
    ml_risk_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    combined_risk_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    carrier: Mapped["Carrier"] = relationship("Carrier", back_populates="shipments")  # noqa: F821
    route: Mapped["Route"] = relationship("Route", back_populates="shipments")  # noqa: F821
    fleet: Mapped["Fleet | None"] = relationship("Fleet", back_populates="shipments")  # noqa: F821
    disruption_links: Mapped[list["ShipmentDisruption"]] = relationship(  # noqa: F821
        "ShipmentDisruption", back_populates="shipment", cascade="all, delete-orphan"
    )
    disruptions: Mapped[list["Disruption"]] = relationship(  # noqa: F821
        "Disruption",
        secondary="shipment_disruptions",
        back_populates="affected_shipments",
        viewonly=True,
    )
    temperature_logs: Mapped[list["TemperatureLog"]] = relationship(  # noqa: F821
        "TemperatureLog", back_populates="shipment"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(  # noqa: F821
        "Recommendation", back_populates="shipment"
    )
