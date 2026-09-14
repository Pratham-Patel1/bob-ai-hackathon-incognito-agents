"""
SupplyChainOS — End-to-End Integration Test Harness (Task 14)

Tests the full intelligence and governance pipeline through the FastAPI layer:
- Disruption impact calculation
- Deterministic + ML predictive risk scoring
- Multi-factor recommendation generation
- Human approval state machine enforcement
- Audit trail recording and retrieval
- Digital Twin in-memory operational isolation
- Cold-chain anomaly tracking
"""
from __future__ import annotations

import uuid
from typing import Any
import pytest
from httpx import ASGITransport, AsyncClient

from backend.database import engine
from backend.main import app


@pytest.fixture
async def client():
    """Async HTTP test client bound to the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as ac:
        yield ac
    await engine.dispose()


@pytest.mark.anyio
async def test_e2e_scenario_1_disruption_to_audit_lifecycle(client: AsyncClient):
    """
    Scenario 1: Full Disruption -> Risk -> Recommendation -> Approval -> Implementation -> Audit
    """
    # 1. Identify an active disruption
    res_disruptions = await client.get("/disruptions?status=active")
    assert res_disruptions.status_code == 200
    disruptions = res_disruptions.json()
    assert len(disruptions) > 0, "Expected at least one active seeded disruption"
    disruption = disruptions[0]
    disruption_id = disruption["id"]

    # 2. Evaluate disruption impact
    res_impact = await client.get(f"/disruptions/{disruption_id}/impact")
    assert res_impact.status_code == 200
    impact_data = res_impact.json()
    assert impact_data["disruption_id"] == disruption_id
    assert "affected_count" in impact_data
    assert isinstance(impact_data["impacted_shipments"], list)

    # 3. Select a valid shipment to test risk calculation
    res_shipments = await client.get("/shipments")
    assert res_shipments.status_code == 200
    shipments = res_shipments.json()
    assert len(shipments) > 0
    test_shipment = shipments[0]
    shipment_id = test_shipment["id"]

    # 4. Call shipment risk endpoint
    res_risk = await client.get(f"/shipments/{shipment_id}/risk")
    assert res_risk.status_code == 200
    risk_data = res_risk.json()
    assert "deterministic_score" in risk_data
    assert 0.0 <= risk_data["deterministic_score"] <= 1.0
    assert "combined_score" in risk_data
    assert 0.0 <= risk_data["combined_score"] <= 1.0
    assert risk_data["risk_level"] in ("low", "medium", "high", "critical")
    assert isinstance(risk_data.get("explanation"), str)
    assert len(risk_data["explanation"]) > 0

    # 5. Generate recommendations for the disruption
    res_gen = await client.post(f"/recommendations/generate?disruption_id={disruption_id}")
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert "created_count" in gen_data
    assert "recommendation_ids" in gen_data

    # 6. Retrieve pending recommendations
    res_recs = await client.get("/recommendations?status=pending")
    assert res_recs.status_code == 200
    pending_recs = res_recs.json()
    assert len(pending_recs) > 0, "Expected at least one pending recommendation"

    target_rec = pending_recs[0]
    rec_id = target_rec["id"]
    assert target_rec["status"] == "pending"

    # 7. Approve the recommendation
    actor_name = "supervisor.sarah"
    approval_payload = {
        "actor": actor_name,
        "notes": "Approved reroute per crisis mitigation protocol.",
    }
    res_approve = await client.post(f"/recommendations/{rec_id}/approve", json=approval_payload)
    assert res_approve.status_code == 200
    approved_data = res_approve.json()
    assert approved_data["status"] == "approved"
    assert approved_data["approved_by"] == actor_name

    # 8. Implement the approved recommendation
    impl_payload = {
        "actor": actor_name,
        "notes": "Carrier notified and new routing dispatched.",
    }
    res_impl = await client.post(f"/recommendations/{rec_id}/implement", json=impl_payload)
    assert res_impl.status_code == 200
    impl_data = res_impl.json()
    assert impl_data["status"] == "implemented"

    # 9. Verify immutable audit trail for the recommendation
    res_audit = await client.get(f"/audit/recommendation/{rec_id}")
    assert res_audit.status_code == 200
    audit_history = res_audit.json()
    assert len(audit_history) >= 2, "Expected at least rec_approved and rec_implemented events"

    actions = [record["action"] for record in audit_history]
    assert "rec_approved" in actions
    assert "rec_implemented" in actions

    # Check actor attribution in audit trail
    approval_audit = next(r for r in audit_history if r["action"] == "rec_approved")
    assert approval_audit["actor"] == actor_name
    assert approval_audit["actor_type"] == "human"
    assert "Crisis mitigation protocol" in approval_audit["reasoning"] or "Approved" in approval_audit["reasoning"]


@pytest.mark.anyio
async def test_e2e_scenario_2_approval_state_machine_protection(client: AsyncClient):
    """
    Scenario 2: State Machine Invariant Protection
    Validates that a recommendation requiring approval cannot be implemented directly while pending.
    """
    # 1. Fetch pending recommendations that require approval
    res_recs = await client.get("/recommendations?status=pending")
    assert res_recs.status_code == 200
    recs = res_recs.json()

    approval_required_recs = [r for r in recs if r.get("requires_approval") is True]

    if not approval_required_recs:
        # Trigger recommendation generation on a seeded critical disruption to ensure a gated candidate exists
        res_disruptions = await client.get("/disruptions")
        disruptions = res_disruptions.json()
        crit_disp = next((d for d in disruptions if d["severity"] == "critical"), disruptions[0])
        await client.post(f"/recommendations/generate?disruption_id={crit_disp['id']}")

        res_recs_retry = await client.get("/recommendations?status=pending")
        recs = res_recs_retry.json()
        approval_required_recs = [r for r in recs if r.get("requires_approval") is True]

    assert len(approval_required_recs) > 0, "Expected at least one recommendation with requires_approval=True"
    test_rec = approval_required_recs[0]
    rec_id = test_rec["id"]

    # 2. Attempt direct implementation while status is still 'pending' -> Expected HTTP 409 Conflict
    direct_impl_payload = {
        "actor": "rogue.operator",
        "notes": "Attempting unauthorized implementation without prior approval.",
    }
    res_illegal_impl = await client.post(f"/recommendations/{rec_id}/implement", json=direct_impl_payload)
    assert res_illegal_impl.status_code == 409, "Expected 409 Conflict when implementing unapproved recommendation"
    assert "requires approval" in res_illegal_impl.json()["detail"].lower()

    # 3. Verify recommendation state remains unmodified as 'pending'
    res_check = await client.get(f"/recommendations/{rec_id}")
    assert res_check.status_code == 200
    assert res_check.json()["status"] == "pending"

    # 4. Now execute legitimate approval
    legit_actor = "supervisor.david"
    res_approve = await client.post(
        f"/recommendations/{rec_id}/approve",
        json={"actor": legit_actor, "notes": "Supervisor authorization granted."},
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "approved"

    # 5. Now execute implementation after legitimate approval -> Expected HTTP 200 OK
    res_legit_impl = await client.post(
        f"/recommendations/{rec_id}/implement",
        json={"actor": legit_actor, "notes": "Operational dispatch confirmed."},
    )
    assert res_legit_impl.status_code == 200
    assert res_legit_impl.json()["status"] == "implemented"


@pytest.mark.anyio
async def test_e2e_scenario_3_digital_twin_operational_isolation(client: AsyncClient):
    """
    Scenario 3: Digital Twin Operational Isolation
    Proves that running what-if simulations produces scenario analytics without altering live operational data.
    """
    # 1. Record baseline live operational state
    res_shipments_before = await client.get("/shipments")
    assert res_shipments_before.status_code == 200
    shipments_before = res_shipments_before.json()
    shipment_count_before = len(shipments_before)
    shipment_status_map_before = {s["id"]: s["status"] for s in shipments_before}

    res_recs_before = await client.get("/recommendations")
    assert res_recs_before.status_code == 200
    recs_count_before = len(res_recs_before.json())

    # 2. Run in-memory Digital Twin what-if simulation
    simulation_payload = {
        "title": "What-If Super Typhoon in North Sea Corridor",
        "disruption_type": "weather",
        "disruption_severity": "critical",
        "epicenter_lat": 54.0,
        "epicenter_lng": 9.5,
        "affected_radius_km": 500.0,
        "affected_route_codes": ["R-EU-01", "R-EU-11", "R-EU-12"],
        "shipment_ids": None,
    }
    res_sim = await client.post("/simulation/run", json=simulation_payload)
    assert res_sim.status_code == 200
    sim_data = res_sim.json()

    # 3. Verify simulation results contain rich scenario analytics
    assert "scenario_summary" in sim_data
    summary = sim_data["scenario_summary"]
    assert summary["name"] == "What-If Super Typhoon in North Sea Corridor"
    assert summary["severity"] == "critical"
    assert "total_affected_shipments" in summary
    assert "total_cargo_value_at_risk_usd" in summary
    assert "top_recommendations" in sim_data
    assert isinstance(sim_data["top_recommendations"], list)

    # 4. Verify live operational data is completely untouched
    res_shipments_after = await client.get("/shipments")
    assert res_shipments_after.status_code == 200
    shipments_after = res_shipments_after.json()
    assert len(shipments_after) == shipment_count_before, "Shipment count must not change after simulation"

    shipment_status_map_after = {s["id"]: s["status"] for s in shipments_after}
    assert shipment_status_map_after == shipment_status_map_before, "Operational shipment statuses must not change"

    res_recs_after = await client.get("/recommendations")
    assert res_recs_after.status_code == 200
    recs_count_after = len(res_recs_after.json())
    assert recs_count_after == recs_count_before, "Operational recommendations must not be persisted by simulation"

    # 5. Verify the intentional simulation audit record was written for traceability
    res_audit = await client.get("/audit?action=simulation_run&limit=5")
    assert res_audit.status_code == 200
    sim_audits = res_audit.json()
    assert len(sim_audits) > 0
    latest_sim_audit = sim_audits[0]
    assert latest_sim_audit["action"] == "simulation_run"
    assert latest_sim_audit["entity_type"] == "simulation"


@pytest.mark.anyio
async def test_e2e_scenario_4_cold_chain_telemetry_flow(client: AsyncClient):
    """
    Scenario 4: Cold-Chain Telemetry & Excursion Flow
    Validates sensor telemetry analysis and temperature thresholding.
    """
    # 1. Fetch all shipments and find temperature-sensitive candidate
    res_shipments = await client.get("/shipments")
    assert res_shipments.status_code == 200
    shipments = res_shipments.json()

    temp_shipments = [s for s in shipments if s.get("temperature_required") is True]
    assert len(temp_shipments) > 0, "Expected at least one seeded temperature-sensitive shipment"
    test_shipment = temp_shipments[0]
    shipment_id = test_shipment["id"]

    # 2. Call temperature log endpoint
    res_temp = await client.get(f"/shipments/{shipment_id}/temperature")
    assert res_temp.status_code == 200
    temp_data = res_temp.json()

    assert temp_data["shipment_id"] == shipment_id
    assert temp_data["temperature_required"] is True
    assert "log_count" in temp_data
    assert isinstance(temp_data.get("logs"), list)

    # 3. If analysis exists, verify cold-chain anomaly schema
    analysis = temp_data.get("analysis")
    if analysis is not None:
        assert isinstance(analysis["has_excursion"], bool)
        assert analysis["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert "recommended_action" in analysis
        assert "explanation" in analysis
        assert isinstance(analysis["explanation"], str)
