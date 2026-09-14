"""Fleet vehicle ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Fleet(Base):
    __tablename__ = "fleet"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vehicle_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # truck/van/rail_car/aircraft/vessel
    carrier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carriers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active/idle/overloaded/maintenance/offline
    current_location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    current_lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    capacity_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    current_load_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    utilization_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    temperature_capable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    temp_min_c: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    temp_max_c: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    carrier: Mapped["Carrier"] = relationship("Carrier", back_populates="fleet_vehicles")  # noqa: F821
    shipments: Mapped[list["Shipment"]] = relationship("Shipment", back_populates="fleet")  # noqa: F821
    temperature_logs: Mapped[list["TemperatureLog"]] = relationship(  # noqa: F821
        "TemperatureLog", back_populates="fleet"
    )
