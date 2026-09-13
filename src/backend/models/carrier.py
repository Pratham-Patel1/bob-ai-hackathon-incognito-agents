"""Carrier ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Carrier(Base):
    __tablename__ = "carriers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # road/rail/air/sea
    reliability_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.8)
    cost_index: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=1.0)
    coverage_regions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    fleet_vehicles: Mapped[list["Fleet"]] = relationship(  # noqa: F821
        "Fleet", back_populates="carrier"
    )
    shipments: Mapped[list["Shipment"]] = relationship(  # noqa: F821
        "Shipment", back_populates="carrier"
    )
