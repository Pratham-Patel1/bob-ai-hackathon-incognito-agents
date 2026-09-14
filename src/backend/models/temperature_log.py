"""TemperatureLog ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class TemperatureLog(Base):
    __tablename__ = "temperature_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False
    )
    fleet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fleet.id"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temperature_c: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    is_excursion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    excursion_severity: Mapped[str] = mapped_column(
        String(10), nullable=False, default="none"
    )  # none/minor/major/critical
    sensor_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="temperature_logs")  # noqa: F821
    fleet: Mapped["Fleet | None"] = relationship("Fleet", back_populates="temperature_logs")  # noqa: F821
