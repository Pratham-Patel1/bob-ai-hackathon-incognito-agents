"""Route ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    origin: Mapped[str] = mapped_column(String(100), nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    waypoints: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # road/rail/air/sea/multimodal
    distance_km: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    typical_duration_hours: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    cost_per_kg_usd: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    reliability_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.85)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    shipments: Mapped[list["Shipment"]] = relationship(  # noqa: F821
        "Shipment", back_populates="route"
    )
