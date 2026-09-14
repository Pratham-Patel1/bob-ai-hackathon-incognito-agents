"""Shipments API router — list, details, risk scoring, ML prediction, cold-chain analysis, route/carrier options."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_async_db
from backend.models.shipment import Shipment
from backend.models.disruption import Disruption
from backend.models.carrier import Carrier
from backend.models.route import Route
from backend.models.temperature_log import TemperatureLog
from backend.schemas.shipment import ShipmentRead
from backend.utils.serializers import (
    shipment_to_dict,
    disruption_to_dict,
    route_to_dict,
    carrier_to_dict,
    temperature_log_to_dict,
)
from backend.engines.shipment_risk import calculate_shipment_risk
from backend.engines.predictive_risk import predict_shipment_risk
from backend.engines.cold_chain_anomaly import analyze_cold_chain
from backend.engines.route_optimizer import optimize_routes
from backend.engines.carrier_recommender import recommend_carriers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get("", response_model=list[ShipmentRead])
async def list_shipments(
    status: str | None = Query(None, description="Filter by status (e.g. in_transit, at_risk, delayed)"),
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    query = select(Shipment).order_by(Shipment.created_at.desc())
    if status:
        query = query.where(Shipment.status == status)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{shipment_id}", response_model=ShipmentRead)
async def get_shipment(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> Any:
    try:
        s_id = uuid.UUID(shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment UUID format")

    result = await session.execute(
        select(Shipment)
        .where(Shipment.id == s_id)
        .options(
            selectinload(Shipment.disruptions),
            selectinload(Shipment.carrier),
            selectinload(Shipment.route),
        )
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@router.get("/{shipment_id}/risk")
async def get_shipment_risk(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Compute multi-factor operational risk score using calculate_shipment_risk."""
    try:
        s_id = uuid.UUID(shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment UUID format")

    result = await session.execute(
        select(Shipment)
        .where(Shipment.id == s_id)
        .options(
            selectinload(Shipment.disruptions),
            selectinload(Shipment.carrier),
            selectinload(Shipment.route),
        )
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    disr_res = await session.execute(select(Disruption).where(Disruption.status != "resolved"))
    active_disruptions = [disruption_to_dict(d) for d in disr_res.scalars().all()]

    shipment_dict = shipment_to_dict(shipment)
    disr_impact = None
    if active_disruptions:
        scores = [float(d.get("impact_score") or d.get("severity_score") or 0) for d in active_disruptions]
        if scores:
            disr_impact = max(scores)

    risk_res = calculate_shipment_risk(
        shipment=shipment_dict,
        disruption_impact_score=disr_impact,
    )
    return {
        "shipment_id": str(shipment.id),
        "risk_score": risk_res.risk_score,
        "risk_level": risk_res.risk_level,
        "deterministic_score": risk_res.deterministic_score,
        "ml_score": risk_res.ml_score,
        "factors": risk_res.factors,
    }


@router.get("/{shipment_id}/prediction")
async def get_shipment_prediction(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Predict delay risk and probability using predict_shipment_risk (Random Forest ML model)."""
    try:
        s_id = uuid.UUID(shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment UUID format")

    result = await session.execute(
        select(Shipment)
        .where(Shipment.id == s_id)
        .options(
            selectinload(Shipment.carrier),
            selectinload(Shipment.route),
        )
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    carrier_dict = carrier_to_dict(shipment.carrier) if shipment.carrier else None
    route_dict = route_to_dict(shipment.route) if shipment.route else None

    features = {
        "disruption_severity_score": 2,
        "cargo_value_usd": float(shipment.cargo_value_usd or 10000),
        "priority_encoded": 1,
        "distance_km": (route_dict.get("distance_km") if route_dict else None) or 500.0,
        "carrier_reliability": (carrier_dict.get("on_time_delivery_rate") if carrier_dict else None) or 0.85,
        "temperature_required": 1 if shipment.temperature_required else 0,
        "is_hazmat": 1 if shipment.cargo_type == "hazmat" else 0,
        "weather_severity": 0,
        "route_risk_index": 0.2,
        "hours_until_deadline": 48.0,
        "shipment_age_hours": 12.0,
    }

    pred_res = predict_shipment_risk(features)
    return {
        "shipment_id": str(shipment.id),
        "delay_probability": pred_res.delay_probability,
        "delay_risk_score": pred_res.delay_risk_score,
        "predicted_delay_hours": pred_res.predicted_delay_hours,
        "model_version": pred_res.model_version,
        "available": pred_res.available,
    }


@router.get("/{shipment_id}/cold-chain")
async def get_shipment_cold_chain(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Analyze IoT sensor history and temperature excursions using analyze_cold_chain."""
    try:
        s_id = uuid.UUID(shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment UUID format")

    result = await session.execute(select(Shipment).where(Shipment.id == s_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    logs_res = await session.execute(
        select(TemperatureLog)
        .where(TemperatureLog.shipment_id == s_id)
        .order_by(TemperatureLog.recorded_at.asc())
    )
    temp_logs = [temperature_log_to_dict(l) for l in logs_res.scalars().all()]

    shipment_dict = shipment_to_dict(shipment)
    cc_res = analyze_cold_chain(temperature_readings=temp_logs, shipment_config=shipment_dict)
    return {
        "shipment_id": str(shipment.id),
        "has_excursion": cc_res.has_excursion,
        "excursion_severity": cc_res.excursion_severity,
        "max_temp_reached": cc_res.max_temp_reached,
        "min_temp_reached": cc_res.min_temp_reached,
        "excursion_duration_mins": cc_res.excursion_duration_mins,
        "spoilage_risk_percent": cc_res.spoilage_risk_percent,
        "excursions": [
            {
                "start_time": str(e.start_time),
                "end_time": str(e.end_time),
                "duration_mins": e.duration_mins,
                "max_deviation_c": e.max_deviation_c,
                "severity": e.severity,
                "reading_count": e.reading_count,
            }
            for e in cc_res.excursions
        ],
        "factors": cc_res.factors,
    }


@router.get("/{shipment_id}/route-options")
async def get_shipment_route_options(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Compute and rank alternative routes avoiding active disruptions using optimize_routes."""
    try:
        s_id = uuid.UUID(shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment UUID format")

    result = await session.execute(
        select(Shipment)
        .where(Shipment.id == s_id)
        .options(selectinload(Shipment.route))
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    routes_res = await session.execute(select(Route).where(Route.active == True))  # noqa: E712
    all_routes = [route_to_dict(r) for r in routes_res.scalars().all()]

    disr_res = await session.execute(select(Disruption).where(Disruption.status != "resolved"))
    active_disruptions = [disruption_to_dict(d) for d in disr_res.scalars().all()]

    shipment_dict = shipment_to_dict(shipment)
    opt_context = {
        "shipment_priority": shipment_dict.get("priority", "medium"),
        "cargo_value_usd": shipment_dict.get("cargo_value_usd", 0.0),
        "temperature_sensitive": shipment_dict.get("temperature_required", False),
        "deadline_hours": 48.0,
    }

    ro_res = optimize_routes(
        routes=all_routes,
        optimization_context=opt_context,
    )
    return {
        "shipment_id": str(shipment.id),
        "recommended_routes": [r.__dict__ for r in ro_res.ranked_routes],
        "top_recommended_route": ro_res.recommended_route.__dict__ if ro_res.recommended_route else None,
        "factors": ro_res.factors,
    }


@router.get("/{shipment_id}/carrier-options")
async def get_shipment_carrier_options(
    shipment_id: str,
    session: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """Rank alternative carriers by reliability, cost, and availability using recommend_carriers."""
    try:
        s_id = uuid.UUID(shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment UUID format")

    result = await session.execute(
        select(Shipment)
        .where(Shipment.id == s_id)
        .options(selectinload(Shipment.carrier))
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    carriers_res = await session.execute(select(Carrier).where(Carrier.active == True))  # noqa: E712
    all_carriers = [carrier_to_dict(c) for c in carriers_res.scalars().all()]

    shipment_dict = shipment_to_dict(shipment)
    shipment_ctx = {
        "required_capacity": (shipment_dict.get("weight_kg", 5000.0) / 1000.0),
        "route_distance_km": float(shipment_dict.get("distance_km") or 500.0),
        "requires_reefer": bool(shipment_dict.get("temperature_required", False)),
        "shipment_priority": shipment_dict.get("priority", "medium"),
    }
    cr_res = recommend_carriers(
        carriers=all_carriers,
        shipment_context=shipment_ctx,
    )
    return {
        "shipment_id": str(shipment.id),
        "ranked_carriers": [c.__dict__ for c in cr_res.ranked_carriers],
        "recommended_carrier": cr_res.recommended_carrier.__dict__ if cr_res.recommended_carrier else None,
        "factors": cr_res.factors,
    }
