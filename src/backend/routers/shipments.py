"""
Shipments router — full Phase 2 implementation.
"""
from __future__ import annotations

import uuid
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_async_db
from backend.config import settings
from backend.models.shipment import Shipment
from backend.models.disruption import Disruption
from backend.models.shipment_disruption import ShipmentDisruption
from backend.models.temperature_log import TemperatureLog
from backend.models.carrier import Carrier
from backend.schemas.shipment import ShipmentRead
from backend.schemas.disruption import DisruptionRead
from backend.utils.audit import write_audit
from backend.engines import shipment_risk, predictive_risk, cold_chain

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/shipments", tags=["shipments"])


def _model_to_dict(obj: Any) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("", response_model=list[ShipmentRead])
async def list_shipments(
    status: str | None = None,
    risk_level: str | None = None,
    carrier_id: str | None = None,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(Shipment).order_by(Shipment.created_at.desc())
    if status:
        query = query.where(Shipment.status == status)
    if risk_level:
        query = query.where(Shipment.risk_level == risk_level)
    if carrier_id:
        query = query.where(Shipment.carrier_id == uuid.UUID(carrier_id))
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{shipment_id}", response_model=ShipmentRead)
async def get_shipment(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    result = await session.execute(
        select(Shipment).where(Shipment.id == uuid.UUID(shipment_id))
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@router.get("/{shipment_id}/risk")
async def get_shipment_risk(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Recalculate deterministic + ML risk scores for a shipment."""
    result = await session.execute(
        select(Shipment).where(Shipment.id == uuid.UUID(shipment_id))
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Load active disruptions for this shipment (via M2M)
    links_result = await session.execute(
        select(ShipmentDisruption).where(
            ShipmentDisruption.shipment_id == uuid.UUID(shipment_id)
        )
    )
    disruption_ids = [link.disruption_id for link in links_result.scalars().all()]

    active_disruptions: list[dict] = []
    if disruption_ids:
        disrupt_result = await session.execute(
            select(Disruption).where(
                Disruption.id.in_(disruption_ids),
                Disruption.status != "resolved",
            )
        )
        active_disruptions = [_model_to_dict(d) for d in disrupt_result.scalars().all()]

    # Load carrier
    carrier_result = await session.execute(
        select(Carrier).where(Carrier.id == shipment.carrier_id)
    )
    carrier_obj = carrier_result.scalar_one_or_none()
    carrier = _model_to_dict(carrier_obj) if carrier_obj else {}

    # Check cold-chain excursion
    has_excursion = False
    if shipment.temperature_required:
        excursion_result = await session.execute(
            select(TemperatureLog).where(
                TemperatureLog.shipment_id == uuid.UUID(shipment_id),
                TemperatureLog.is_excursion == True,  # noqa: E712
            )
        )
        has_excursion = excursion_result.scalar_one_or_none() is not None

    shipment_dict = _model_to_dict(shipment)
    # Enrich with route reliability for ML features
    shipment_dict["route_reliability_score"] = 0.8  # default; refined if route loaded

    det_result = shipment_risk.run(
        shipment=shipment_dict,
        active_disruptions=active_disruptions,
        temperature_excursion=has_excursion,
        carrier=carrier,
    )
    ml_result = predictive_risk.run(
        shipment=shipment_dict,
        active_disruptions=active_disruptions,
        carrier=carrier,
    )

    det_w = settings.ml_deterministic_weight
    ml_w = settings.ml_predictive_weight
    if ml_result.ml_score is not None:
        combined = det_w * det_result.score + ml_w * ml_result.ml_score
    else:
        combined = det_result.score

    # Persist updated risk scores
    prev_state = {"risk_score": float(shipment.risk_score), "risk_level": shipment.risk_level}
    shipment.risk_score = det_result.score
    shipment.risk_level = det_result.level
    shipment.ml_risk_score = ml_result.ml_score
    shipment.combined_risk_score = round(combined, 4)

    await write_audit(
        session=session,
        entity_type="shipment",
        entity_id=shipment.id,
        action="risk_calculated",
        actor="system",
        actor_type="system",
        reasoning=det_result.explanation,
        previous_state=prev_state,
        new_state={"risk_score": det_result.score, "risk_level": det_result.level},
        extra_metadata={
            "ml_score": ml_result.ml_score,
            "combined_score": round(combined, 4),
            "model_version": ml_result.model_version,
            "disruption_count": len(active_disruptions),
        },
    )
    await session.commit()

    return {
        "shipment_id": shipment_id,
        "deterministic_score": det_result.score,
        "ml_score": ml_result.ml_score,
        "combined_score": round(combined, 4),
        "risk_level": det_result.level,
        "explanation": det_result.explanation,
        "factors": [
            {"name": f.name, "value": f.value, "contribution": f.contribution}
            for f in det_result.factors
        ],
        "ml_top_features": [
            {"feature": fc.feature_name, "value": fc.value, "importance": fc.importance}
            for fc in ml_result.top_features
        ],
        "model_version": ml_result.model_version,
    }


@router.get("/{shipment_id}/disruptions", response_model=list[DisruptionRead])
async def get_shipment_disruptions(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """All active disruptions affecting this shipment (via M2M table)."""
    links_result = await session.execute(
        select(ShipmentDisruption).where(
            ShipmentDisruption.shipment_id == uuid.UUID(shipment_id)
        )
    )
    disruption_ids = [link.disruption_id for link in links_result.scalars().all()]
    if not disruption_ids:
        return []
    result = await session.execute(
        select(Disruption).where(
            Disruption.id.in_(disruption_ids),
            Disruption.status != "resolved",
        )
    )
    return result.scalars().all()


@router.get("/{shipment_id}/temperature")
async def get_shipment_temperature(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Temperature log history + cold-chain analysis for a shipment."""
    shipment_result = await session.execute(
        select(Shipment).where(Shipment.id == uuid.UUID(shipment_id))
    )
    shipment = shipment_result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    logs_result = await session.execute(
        select(TemperatureLog)
        .where(TemperatureLog.shipment_id == uuid.UUID(shipment_id))
        .order_by(TemperatureLog.recorded_at.asc())
    )
    logs = logs_result.scalars().all()
    log_dicts = [_model_to_dict(lg) for lg in logs]

    analysis = None
    if shipment.temperature_required and shipment.temp_min_c and shipment.temp_max_c:
        analysis_result = cold_chain.run(
            temperature_logs=log_dicts,
            temp_min_c=float(shipment.temp_min_c),
            temp_max_c=float(shipment.temp_max_c),
        )
        analysis = {
            "has_excursion": analysis_result.has_excursion,
            "severity": analysis_result.severity,
            "excursion_count": analysis_result.excursion_count,
            "max_deviation_c": analysis_result.max_deviation_c,
            "total_excursion_minutes": analysis_result.total_excursion_minutes,
            "recommended_action": analysis_result.recommended_action,
            "explanation": analysis_result.explanation,
        }

    return {
        "shipment_id": shipment_id,
        "temperature_required": shipment.temperature_required,
        "temp_min_c": float(shipment.temp_min_c) if shipment.temp_min_c else None,
        "temp_max_c": float(shipment.temp_max_c) if shipment.temp_max_c else None,
        "log_count": len(logs),
        "logs": [
            {
                "recorded_at": lg.recorded_at.isoformat(),
                "temperature_c": float(lg.temperature_c),
                "is_excursion": lg.is_excursion,
                "excursion_severity": lg.excursion_severity,
            }
            for lg in logs
        ],
        "cold_chain_analysis": analysis,
    }


@router.post("/bulk-risk-refresh")
async def bulk_risk_refresh(
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    """Recalculate risk scores for all active shipments."""
    active_result = await session.execute(
        select(Shipment).where(Shipment.status.in_(["in_transit", "at_risk", "delayed"]))
    )
    active_shipments = active_result.scalars().all()

    # Load all carriers for lookup
    carriers_result = await session.execute(select(Carrier))
    carriers_by_id = {str(c.id): _model_to_dict(c) for c in carriers_result.scalars().all()}

    updated = 0
    for shipment in active_shipments:
        sid = str(shipment.id)
        links_result = await session.execute(
            select(ShipmentDisruption).where(ShipmentDisruption.shipment_id == shipment.id)
        )
        disruption_ids = [link.disruption_id for link in links_result.scalars().all()]
        active_disruptions: list[dict] = []
        if disruption_ids:
            dr = await session.execute(
                select(Disruption).where(
                    Disruption.id.in_(disruption_ids),
                    Disruption.status != "resolved",
                )
            )
            active_disruptions = [_model_to_dict(d) for d in dr.scalars().all()]

        carrier = carriers_by_id.get(str(shipment.carrier_id), {})
        shipment_dict = _model_to_dict(shipment)
        shipment_dict["route_reliability_score"] = 0.8

        det = shipment_risk.run(shipment_dict, active_disruptions, carrier=carrier)
        ml = predictive_risk.run(shipment_dict, active_disruptions, carrier)

        det_w = settings.ml_deterministic_weight
        ml_w = settings.ml_predictive_weight
        combined = (
            det_w * det.score + ml_w * ml.ml_score
            if ml.ml_score is not None
            else det.score
        )

        shipment.risk_score = det.score
        shipment.risk_level = det.level
        shipment.ml_risk_score = ml.ml_score
        shipment.combined_risk_score = round(combined, 4)
        updated += 1

    await session.commit()
    return {"updated_count": updated, "status": "ok"}
