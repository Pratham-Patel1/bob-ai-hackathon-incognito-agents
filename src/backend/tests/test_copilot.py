"""
SupplyChainOS — AI Copilot ↔ MCP Integration Test Suite.
Validates natural-language intent parsing, dynamic MCP tool dispatch, operational explanations,
approval state machine protection, and secure error isolation.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app
from backend.database import engine


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as ac:
        yield ac
    await engine.dispose()


# ── 1. Disruption Impact Intent ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_disruption_query(async_client: AsyncClient):
    """Test 'Which shipments are affected by the active storm?' routes to analyze_disruption."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "Which shipments are affected by the active storm in the North Sea?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "analyze_disruption"
    assert data["status"] == "success"
    assert "Disruption Threat Intelligence" in data["explanation"]
    assert "disruption_id" in data["tool_arguments"]


# ── 2. Shipment Risk Intent ───────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_shipment_risk_query(async_client: AsyncClient):
    """Test 'What is the risk of shipment SHP-0005?' routes to get_shipment_risk."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "What is the risk of shipment SHP-0005?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "get_shipment_risk"
    assert data["status"] == "success"
    assert "Shipment Risk Assessment" in data["explanation"]
    assert "Risk Score" in data["explanation"]


# ── 3. Route & Alternatives Intent ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_route_query(async_client: AsyncClient):
    """Test 'Which alternative routes are available?' routes to find_alternative_routes."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "Which alternative routes and bypass corridors are available?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "find_alternative_routes"
    assert data["status"] == "success"
    assert "Alternative Bypass Route" in data["explanation"] or "Route Analysis" in data["explanation"]


# ── 4. Cold Chain Intent ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_cold_chain_query(async_client: AsyncClient):
    """Test 'Are there cold-chain temperature excursions?' routes to check_cold_chain."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "Are there cold-chain temperature excursions or sensor spoilage warnings?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "check_cold_chain"
    assert data["status"] == "success"
    assert "Cold Chain IoT Telemetry" in data["explanation"]


# ── 5. Fleet Intelligence Intent ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_fleet_query(async_client: AsyncClient):
    """Test 'Which fleet vehicles are idle?' routes to get_fleet_status."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "Which fleet vehicles and trucks are idle and available for redeployment?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "get_fleet_status"
    assert data["status"] == "success"
    assert "Fleet Intelligence" in data["explanation"]
    assert data["tool_arguments"]["status"] == "idle"


# ── 6. Business Impact Intent ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_business_impact_query(async_client: AsyncClient):
    """Test 'What is the business impact of this disruption?' routes to get_cascade_impact."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "What is the business impact and cost of this disruption?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "get_cascade_impact"
    assert data["status"] == "success"
    assert "Disruption Business & Cascade Impact Analysis" in data["explanation"]
    assert "Cargo Value at Risk" in data["explanation"]
    assert "Estimated Delay Cost" in data["explanation"]
    assert "SLA Penalty Exposure" in data["explanation"]


# ── 7. Cascade Impact Intent ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_cascade_impact_query(async_client: AsyncClient):
    """Test 'What is the cascade impact of this disruption?' routes to get_cascade_impact."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "What is the cascade ripple impact of this disruption?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "get_cascade_impact"
    assert data["status"] == "success"
    assert "Cascade Impact" in data["explanation"]


# ── 8. Digital Twin Simulation Intent ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_digital_twin_simulation(async_client: AsyncClient):
    """Test 'Simulate what happens if this disruption affects route RT-01' routes to simulate_scenario."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "Simulate what happens if this critical disruption affects route RT-01 in the digital twin."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "simulate_scenario"
    assert data["status"] == "success"
    assert "Digital Twin In-Memory Simulation" in data["explanation"]
    assert "RT-01" in data["tool_arguments"]["affected_route_codes"]


# ── 9. Recommendations Intent ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_recommendations_query(async_client: AsyncClient):
    """Test 'Show me the current recommendations' routes to get_recommendations."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "Show me the current AI recommendations and mitigation actions."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "get_recommendations"
    assert data["status"] == "success"
    assert "SupplyChainOS AI Recommendations" in data["explanation"]


# ── 10. Human Approval Protection Gate ────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_approval_protection_rejection_without_actor(async_client: AsyncClient):
    """Test approval without human actor identity is rejected by governance safety gate."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "Approve recommendation REC-001 now"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "approve_recommendation"
    assert data["status"] == "approval_required"
    assert data["requires_human_approval"] is True
    assert "Human Approval Required" in data["explanation"]
    assert data["tool_result"]["error"] == "Human approval credentials missing"


@pytest.mark.asyncio
async def test_copilot_approval_with_valid_actor(async_client: AsyncClient):
    """Test approval with authenticated human operator identity successfully dispatches through MCP."""
    # First fetch recommendations to obtain a valid recommendation ID
    recs_res = await async_client.get("/recommendations")
    recs = recs_res.json()
    assert len(recs) > 0
    rec_id = recs[0]["id"]

    res = await async_client.post(
        "/copilot/query",
        json={
            "query": f"Approve recommendation {rec_id}",
            "actor": "Lead Controller Jane Doe",
            "notes": "Verified reroute fuel budget & customer SLA tolerance.",
            "shipment_id": rec_id,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_called"] == "approve_recommendation"
    assert data["status"] == "success"
    assert "Recommendation Approved" in data["explanation"]
    assert "Lead Controller Jane Doe" in data["explanation"]


# ── 11. Invalid Input & Error Handling ────────────────────────────────────────
@pytest.mark.asyncio
async def test_copilot_invalid_input(async_client: AsyncClient):
    """Test validation reject on empty or single-character query."""
    res = await async_client.post(
        "/copilot/query",
        json={"query": "x"},
    )
    assert res.status_code == 422
