"""
Integration test suite for FastAPI REST API endpoints connected to the 10 intelligence engines.
Verifies routing, serialization, engine invocation, and responses.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.database import get_async_db
from backend.models.shipment import Shipment
from backend.models.disruption import Disruption
from backend.models.route import Route
from backend.models.carrier import Carrier
from backend.models.fleet import Fleet
from backend.models.temperature_log import TemperatureLog
from backend.models.recommendation import Recommendation


def create_sample_entities():
    s_id = uuid.uuid4()
    r_id = uuid.uuid4()
    c_id = uuid.uuid4()
    f_id = uuid.uuid4()
    d_id = uuid.uuid4()
    rec_id = uuid.uuid4()

    now = datetime.now(timezone.utc)

    sample_route = Route(
        id=r_id,
        code="RT-TEST-01",
        name="Test Corridor Express",
        origin="Port City",
        destination="Metro Hub",
        mode="road",
        distance_km=450.0,
        typical_duration_hours=9.0,
        cost_per_kg_usd=2.85,
        reliability_score=0.92,
        waypoints=[{"lat": 18.98, "lng": 72.84, "name": "CheckPoint 1"}],
        active=True,
        created_at=now,
    )

    sample_carrier = Carrier(
        id=c_id,
        name="Apex Logistics",
        code="APEX",
        type="road",
        reliability_score=0.94,
        cost_index=1.1,
        coverage_regions=["West Coast", "Central"],
        contact_name="Alice Smith",
        contact_email="alice@apex.com",
        active=True,
        created_at=now,
    )

    sample_shipment = Shipment(
        id=s_id,
        tracking_number="TRK-TEST-9999",
        origin="Port City",
        destination="Metro Hub",
        origin_lat=18.95,
        origin_lng=72.82,
        destination_lat=19.07,
        destination_lng=72.87,
        current_location="Port Gate 4",
        current_lat=18.96,
        current_lng=72.83,
        carrier_id=c_id,
        route_id=r_id,
        fleet_id=f_id,
        status="in_transit",
        scheduled_departure=now,
        scheduled_arrival=now,
        estimated_arrival=now,
        actual_arrival=None,
        cargo_type="temperature_sensitive",
        cargo_value_usd=150000.0,
        weight_kg=2500.0,
        temperature_required=True,
        temp_min_c=2.0,
        temp_max_c=8.0,
        risk_score=45.0,
        risk_level="medium",
        ml_risk_score=40.0,
        combined_risk_score=43.0,
        carrier=sample_carrier,
        route=sample_route,
        disruptions=[],
        created_at=now,
        updated_at=now,
    )

    sample_disruption = Disruption(
        id=d_id,
        type="weather",
        severity="HIGH",
        title="Flash Flooding Test",
        description="Heavy rainfall blocking NH-48",
        epicenter_lat=18.98,
        epicenter_lng=72.84,
        affected_radius_km=50.0,
        affected_route_codes=["RT-TEST-01"],
        status="active",
        start_time=now,
        estimated_end_time=now,
        created_at=now,
        updated_at=now,
    )

    sample_fleet = Fleet(
        id=f_id,
        vehicle_id="FLT-TRK-101",
        type="truck",
        carrier_id=c_id,
        status="available",
        current_location="Yard 2",
        current_lat=18.97,
        current_lng=72.83,
        capacity_kg=25000.0,
        current_load_kg=0.0,
        utilization_pct=0.0,
        temperature_capable=True,
        created_at=now,
        updated_at=now,
    )

    sample_temp_log = TemperatureLog(
        id=uuid.uuid4(),
        shipment_id=s_id,
        recorded_at=now,
        temperature_c=11.5,
        is_excursion=True,
        excursion_severity="major",
        location="Highway Checkpoint",
        created_at=now,
    )

    sample_rec = Recommendation(
        id=rec_id,
        shipment_id=s_id,
        disruption_id=d_id,
        type="reroute",
        priority="high",
        title="Reroute via Western Bypass",
        description="Avoid flooded section of NH-48",
        reason="Heavy flood risk on primary corridor",
        reasoning_factors=["Disruption severity HIGH (+45)"],
        status="pending",
        requires_approval=True,
        approved_by=None,
        approved_at=None,
        created_at=now,
        updated_at=now,
    )

    return {
        "shipment": sample_shipment,
        "disruption": sample_disruption,
        "route": sample_route,
        "carrier": sample_carrier,
        "fleet": sample_fleet,
        "temp_log": sample_temp_log,
        "recommendation": sample_rec,
    }


from contextlib import asynccontextmanager


@asynccontextmanager
async def dummy_lifespan(app):
    yield


@pytest.fixture
def test_client():
    data = create_sample_entities()
    app = create_app()
    app.router.lifespan_context = dummy_lifespan

    async def mock_get_db():
        session = AsyncMock()

        async def mock_execute(statement, *args, **kwargs):
            mock_res = MagicMock()
            st_str = str(statement).lower()

            if "from shipments" in st_str:
                mock_res.scalar_one_or_none.return_value = data["shipment"]
                mock_res.scalars.return_value.all.return_value = [data["shipment"]]
            elif "from disruptions" in st_str:
                if "where disruptions.id =" in st_str:
                    mock_res.scalar_one_or_none.return_value = data["disruption"]
                else:
                    mock_res.scalars.return_value.all.return_value = [data["disruption"]]
            elif "from routes" in st_str:
                if "where routes.id =" in st_str:
                    mock_res.scalar_one_or_none.return_value = data["route"]
                else:
                    mock_res.scalars.return_value.all.return_value = [data["route"]]
            elif "from carriers" in st_str:
                if "where carriers.id =" in st_str:
                    mock_res.scalar_one_or_none.return_value = data["carrier"]
                else:
                    mock_res.scalars.return_value.all.return_value = [data["carrier"]]
            elif "from fleet" in st_str:
                mock_res.scalars.return_value.all.return_value = [data["fleet"]]
            elif "from temperature_logs" in st_str:
                mock_res.scalars.return_value.all.return_value = [data["temp_log"]]
            elif "from recommendations" in st_str:
                if "where recommendations.id =" in st_str:
                    mock_res.scalar_one_or_none.return_value = data["recommendation"]
                else:
                    mock_res.scalars.return_value.all.return_value = [data["recommendation"]]
            elif "from decision_audit" in st_str:
                mock_res.scalars.return_value.all.return_value = []
            else:
                mock_res.scalar_one_or_none.return_value = None
                mock_res.scalars.return_value.all.return_value = []

            return mock_res

        session.execute.side_effect = mock_execute
        yield session

    app.dependency_overrides[get_async_db] = mock_get_db
    with TestClient(app) as client:
        yield client, data


def test_list_shipments(test_client):
    client, data = test_client
    resp = client.get("/api/v1/shipments")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert resp.json()[0]["tracking_number"] == data["shipment"].tracking_number


def test_get_shipment_details(test_client):
    client, data = test_client
    s_id = str(data["shipment"].id)
    resp = client.get(f"/api/v1/shipments/{s_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == s_id


def test_shipment_risk_endpoint(test_client):
    client, data = test_client
    s_id = str(data["shipment"].id)
    resp = client.get(f"/api/v1/shipments/{s_id}/risk")
    assert resp.status_code == 200
    body = resp.json()
    assert "risk_score" in body
    assert "risk_level" in body
    assert "factors" in body
    assert len(body["factors"]) > 0


def test_shipment_prediction_endpoint(test_client):
    client, data = test_client
    s_id = str(data["shipment"].id)
    resp = client.get(f"/api/v1/shipments/{s_id}/prediction")
    assert resp.status_code == 200
    body = resp.json()
    assert "delay_probability" in body
    assert "delay_risk_score" in body
    assert "predicted_delay_hours" in body


def test_shipment_cold_chain_endpoint(test_client):
    client, data = test_client
    s_id = str(data["shipment"].id)
    resp = client.get(f"/api/v1/shipments/{s_id}/cold-chain")
    assert resp.status_code == 200
    body = resp.json()
    assert "has_excursion" in body
    assert "excursion_severity" in body
    assert "spoilage_risk_percent" in body


def test_shipment_route_options_endpoint(test_client):
    client, data = test_client
    s_id = str(data["shipment"].id)
    resp = client.get(f"/api/v1/shipments/{s_id}/route-options")
    assert resp.status_code == 200
    body = resp.json()
    assert "recommended_routes" in body
    assert "factors" in body


def test_shipment_carrier_options_endpoint(test_client):
    client, data = test_client
    s_id = str(data["shipment"].id)
    resp = client.get(f"/api/v1/shipments/{s_id}/carrier-options")
    assert resp.status_code == 200
    body = resp.json()
    assert "ranked_carriers" in body


def test_disruption_impact_endpoint(test_client):
    client, data = test_client
    d_id = str(data["disruption"].id)
    resp = client.get(f"/api/v1/disruptions/{d_id}/impact")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_shipments_evaluated" in body
    assert "affected_shipments_count" in body
    assert "affected_shipments" in body


def test_fleet_intelligence_endpoint(test_client):
    client, data = test_client
    resp = client.get("/api/v1/fleet/intelligence")
    assert resp.status_code == 200
    body = resp.json()
    assert "summary" in body
    assert "average_utilisation_percent" in body["summary"]


def test_route_simulation_endpoint(test_client):
    client, data = test_client
    s_id = str(data["shipment"].id)
    r_id = str(data["route"].id)
    c_id = str(data["carrier"].id)

    payload = {
        "shipment_id": s_id,
        "candidate_route_id": r_id,
        "candidate_carrier_id": c_id,
    }
    resp = client.post("/api/v1/simulations/route", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "baseline" in body
    assert "simulated" in body
    assert "delta" in body
    assert "business_impact" in body


def test_scenario_simulation_endpoint(test_client):
    client, data = test_client
    payload = {
        "title": "Cyclone Alert Scenario",
        "disruption_type": "cyclone",
        "disruption_severity": "high",
        "epicenter_lat": 18.98,
        "epicenter_lng": 72.84,
        "affected_radius_km": 100.0,
        "affected_route_codes": ["RT-TEST-01"],
    }
    resp = client.post("/api/v1/simulations/scenario", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "affected_shipment_count" in body
    assert "risk_scores" in body
    assert "scenario_summary" in body


def test_recommendation_generate_endpoint(test_client):
    client, data = test_client
    s_id = str(data["shipment"].id)
    resp = client.post(f"/api/v1/recommendations/generate?shipment_id={s_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "recommendations" in body


def test_recommendation_approve_endpoint(test_client):
    client, data = test_client
    rec_id = str(data["recommendation"].id)
    payload = {
        "actor": "Supply Chain Dispatcher 01",
        "notes": "Approved alternative route due to flood alert",
    }
    resp = client.post(f"/api/v1/recommendations/{rec_id}/approve", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["approved_by"] == "Supply Chain Dispatcher 01"


def test_recommendation_reject_endpoint(test_client):
    client, data = test_client
    data["recommendation"].status = "pending"
    rec_id = str(data["recommendation"].id)
    payload = {
        "actor": "Lead Logistics Officer",
        "notes": "Cost increase unacceptable",
    }
    resp = client.post(f"/api/v1/recommendations/{rec_id}/reject", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected"
