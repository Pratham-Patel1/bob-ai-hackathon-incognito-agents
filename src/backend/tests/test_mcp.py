"""
SupplyChainOS — Model Context Protocol (MCP) Test Suite.

Validates all 9 MCP tools, schema validation, security allowlists, DB isolation,
approval protections, error masking, and JSON-RPC 2.0 protocol compliance.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.database import engine
from backend.main import app
from backend.mcp.client import BackendAPIClient
from backend.mcp.server import SupplyChainOSMCPServer, MCP_TOOL_DEFINITIONS
from backend.mcp.security import (
    ALLOWED_TOOLS,
    MCPSecurityError,
    validate_tool_allowed,
    sanitize_input_strings,
    mask_sensitive_error,
)

from backend.mcp.schemas import (
    AnalyzeDisruptionInput,
    GetShipmentRiskInput,
    CheckColdChainInput,
    GetFleetStatusInput,
    FindAlternativeRoutesInput,
    SimulateScenarioInput,
    GetRecommendationsInput,
    ApproveRecommendationInput,
    GetCascadeImpactInput,
)


@pytest.fixture
async def mcp_server():
    """Create an MCP server instance wired to the in-process FastAPI application."""
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver/api/v1",
    ) as ac:
        api_client = BackendAPIClient(
            base_url="http://testserver/api/v1",
            http_client=ac,
        )

        server = SupplyChainOSMCPServer(api_client=api_client)

        yield server

    await engine.dispose()


# ── 1. Security & Allowlist Tests ──────────────────────────────────────────────


def test_mcp_allowlist_completeness():
    """Verify that all 9 required MCP tools are present in the allowlist."""

    expected_tools = {
        "analyze_disruption",
        "get_shipment_risk",
        "check_cold_chain",
        "get_fleet_status",
        "find_alternative_routes",
        "simulate_scenario",
        "get_recommendations",
        "approve_recommendation",
        "get_cascade_impact",
    }

    assert ALLOWED_TOOLS == expected_tools
    assert len(MCP_TOOL_DEFINITIONS) == 9

    server_tools = {t["name"] for t in MCP_TOOL_DEFINITIONS}

    assert server_tools == expected_tools


def test_mcp_unallowed_tool_rejection():
    """Ensure unauthorized or hallucinated tools are strictly rejected."""

    with pytest.raises(MCPSecurityError) as exc_info:
        validate_tool_allowed("execute_sql_query")

    assert "not in the authorized" in str(exc_info.value)

    with pytest.raises(MCPSecurityError):
        validate_tool_allowed("drop_table")


def test_mcp_sql_injection_defense():
    """Ensure SQL injection patterns in parameters are intercepted and blocked."""

    with pytest.raises(MCPSecurityError) as exc_info:
        sanitize_input_strings(
            {"search": "'; DROP TABLE shipments; --"}
        )

    assert "dangerous" in str(exc_info.value).lower()


def test_mcp_error_masking():
    """Verify that credentials and internal database paths are masked in error outputs."""

    raw_error = Exception(
        "Connection error to postgresql://admin:TEST_PASSWORD@db:5432/supplychainos"
    )

    masked = mask_sensitive_error(raw_error)

    assert "TEST_PASSWORD" not in masked


def test_mcp_no_direct_database_import():
    """Architectural constraint: Ensure MCP module does not import SQLAlchemy Session or engine."""

    import backend.mcp.client as client_mod
    import backend.mcp.tools as tools_mod
    import backend.mcp.server as server_mod

    for mod in [client_mod, tools_mod, server_mod]:
        assert not hasattr(mod, "AsyncSession")
        assert not hasattr(mod, "get_async_db")
        assert not hasattr(mod, "engine")


# ── 2. Tool Validation Schema Tests ───────────────────────────────────────────


def test_schema_analyze_disruption_validation():
    valid_uuid = str(uuid.uuid4())

    inp = AnalyzeDisruptionInput(disruption_id=valid_uuid)

    assert inp.disruption_id == valid_uuid

    with pytest.raises(Exception):
        AnalyzeDisruptionInput(disruption_id="invalid-not-a-uuid")


def test_schema_get_shipment_risk_validation():
    valid_uuid = str(uuid.uuid4())

    inp = GetShipmentRiskInput(shipment_id=valid_uuid)

    assert inp.shipment_id == valid_uuid

    with pytest.raises(Exception):
        GetShipmentRiskInput(shipment_id="")


def test_schema_check_cold_chain_validation():
    valid_uuid = str(uuid.uuid4())

    inp = CheckColdChainInput(shipment_id=valid_uuid)

    assert inp.shipment_id == valid_uuid

    with pytest.raises(Exception):
        CheckColdChainInput(shipment_id="12345")


def test_schema_get_fleet_status_validation():
    inp1 = GetFleetStatusInput(status="idle")

    assert inp1.status == "idle"

    inp2 = GetFleetStatusInput()

    assert inp2.status == "all"

    with pytest.raises(Exception):
        GetFleetStatusInput(status="unknown_status")  # type: ignore


def test_schema_simulate_scenario_validation():
    valid_scenario = {
        "title": "North Sea Storm Simulation",
        "disruption_type": "severe_weather",
        "disruption_severity": "critical",
        "epicenter_lat": 54.0,
        "epicenter_lng": 9.5,
        "affected_radius_km": 250.0,
        "affected_route_codes": ["RT-01"],
    }

    inp = SimulateScenarioInput(**valid_scenario)

    assert inp.title == "North Sea Storm Simulation"
    assert inp.epicenter_lat == 54.0

    # Latitude out of bounds
    with pytest.raises(Exception):
        SimulateScenarioInput(
            **{**valid_scenario, "epicenter_lat": 95.0}
        )

    # Radius <= 0
    with pytest.raises(Exception):
        SimulateScenarioInput(
            **{**valid_scenario, "affected_radius_km": -10.0}
        )


def test_schema_approve_recommendation_protection():
    valid_uuid = str(uuid.uuid4())

    inp = ApproveRecommendationInput(
        recommendation_id=valid_uuid,
        actor="Operations Dispatcher 01",
        notes="Approved via emergency protocol",
    )

    assert inp.actor == "Operations Dispatcher 01"

    # Anonymous or empty actor must be rejected
    with pytest.raises(Exception):
        ApproveRecommendationInput(
            recommendation_id=valid_uuid,
            actor="",
        )

    with pytest.raises(Exception):
        ApproveRecommendationInput(
            recommendation_id=valid_uuid,
            actor="anonymous",
        )


# ── 3. Tool Execution & API Integration Tests ─────────────────────────────────


@pytest.mark.anyio
async def test_tool_analyze_disruption(mcp_server: SupplyChainOSMCPServer):
    """Test 1: analyze_disruption tool retrieves impact data for a disruption."""

    # First get an active disruption from backend
    recs_res = await mcp_server.client._request("GET", "/disruptions")

    assert isinstance(recs_res, list)
    assert len(recs_res) > 0

    disruption_id = recs_res[0]["id"]

    res = await mcp_server.call_tool(
        "analyze_disruption",
        {"disruption_id": disruption_id},
    )

    assert res["status"] == "success"
    assert res["tool"] == "analyze_disruption"

    content = res["content"]

    assert content["disruption_id"] == disruption_id
    assert "affected_count" in content
    assert "impacted_shipments" in content


@pytest.mark.anyio
async def test_tool_get_shipment_risk(mcp_server: SupplyChainOSMCPServer):
    """Test 2: get_shipment_risk tool retrieves combined deterministic and ML risk scores."""

    shipments = await mcp_server.client._request("GET", "/shipments")

    assert isinstance(shipments, list)
    assert len(shipments) > 0

    shipment_id = shipments[0]["id"]

    res = await mcp_server.call_tool(
        "get_shipment_risk",
        {"shipment_id": shipment_id},
    )

    assert res["status"] == "success"

    content = res["content"]

    assert content["shipment_id"] == shipment_id
    assert "deterministic_score" in content
    assert "combined_score" in content
    assert "risk_level" in content


@pytest.mark.anyio
async def test_tool_check_cold_chain(mcp_server: SupplyChainOSMCPServer):
    """Test 3: check_cold_chain tool retrieves sensor history and excursion metrics."""

    shipments = await mcp_server.client._request("GET", "/shipments")

    assert isinstance(shipments, list)
    assert len(shipments) > 0

    pharma_shipment = next(
        (
            s
            for s in shipments
            if s.get("temperature_required")
        ),
        shipments[0],
    )

    shipment_id = pharma_shipment["id"]

    res = await mcp_server.call_tool(
        "check_cold_chain",
        {"shipment_id": shipment_id},
    )

    assert res["status"] == "success"

    content = res["content"]

    assert content["shipment_id"] == shipment_id
    assert "logs" in content


@pytest.mark.anyio
async def test_tool_get_fleet_status(mcp_server: SupplyChainOSMCPServer):
    """Test 4: get_fleet_status tool retrieves fleet metrics and redeployment options."""

    res = await mcp_server.call_tool(
        "get_fleet_status",
        {"status": "all"},
    )

    assert res["status"] == "success"

    content = res["content"]

    assert (
        "fleet_analysis" in content
        or "result" in content
        or isinstance(content, list)
    )


@pytest.mark.anyio
async def test_tool_find_alternative_routes(mcp_server: SupplyChainOSMCPServer):
    """Test 5: find_alternative_routes tool retrieves alternative bypass routes."""

    routes = await mcp_server.client._request("GET", "/routes")

    assert isinstance(routes, list)
    assert len(routes) > 0

    route_id = routes[0]["id"]

    res = await mcp_server.call_tool(
        "find_alternative_routes",
        {"route_id": route_id},
    )

    assert res["status"] == "success"

    content = res["content"]

    assert "alternative_routes" in content
    assert isinstance(content["alternative_routes"], list)


@pytest.mark.anyio
async def test_tool_simulate_scenario(mcp_server: SupplyChainOSMCPServer):
    """Test 6: simulate_scenario tool runs an in-memory Digital Twin scenario."""

    scenario = {
        "title": "MCP Simulated Weather Hazard",
        "disruption_type": "severe_weather",
        "disruption_severity": "critical",
        "epicenter_lat": 54.0,
        "epicenter_lng": 9.5,
        "affected_radius_km": 200.0,
        "affected_route_codes": ["RT-01"],
    }

    res = await mcp_server.call_tool(
        "simulate_scenario",
        scenario,
    )

    assert res["status"] == "success"

    content = res["content"]

    assert "scenario_summary" in content
    assert "affected_shipment_count" in content
    assert "top_recommendations" in content


@pytest.mark.anyio
async def test_tool_get_recommendations(mcp_server: SupplyChainOSMCPServer):
    """Test 7: get_recommendations tool returns system recommendations."""

    res = await mcp_server.call_tool(
        "get_recommendations",
        {"status": "pending"},
    )

    assert res["status"] == "success"

    content = res["content"]

    assert "recommendations" in content
    assert isinstance(content["recommendations"], list)


@pytest.mark.anyio
async def test_tool_approve_recommendation_and_audit(
    mcp_server: SupplyChainOSMCPServer,
):
    """Test 8: approve_recommendation tool executes state machine transition and writes audit log."""

    # Ensure at least one pending recommendation exists
    disruptions = await mcp_server.client._request(
        "GET",
        "/disruptions",
    )

    if disruptions:
        await mcp_server.client._request(
            "POST",
            f"/recommendations/generate?disruption_id={disruptions[0]['id']}",
        )

    pending_recs = await mcp_server.client._request(
        "GET",
        "/recommendations?status=pending",
    )

    assert isinstance(pending_recs, list)
    assert len(pending_recs) > 0

    rec_to_approve = pending_recs[0]["id"]

    res = await mcp_server.call_tool(
        "approve_recommendation",
        {
            "recommendation_id": rec_to_approve,
            "actor": "Chief Dispatcher John",
            "notes": "Approved via Bob Copilot MCP tool",
        },
    )

    assert res["status"] == "success"

    content = res["content"]

    assert content["status"] == "approved"
    assert content["approved_by"] == "Chief Dispatcher John"

    # Verify audit trail
    audits = await mcp_server.client._request(
        "GET",
        f"/audit/recommendation/{rec_to_approve}",
    )

    assert isinstance(audits, list)
    assert len(audits) > 0

    assert any(
        a["action"] == "rec_approved"
        and a["actor"] == "Chief Dispatcher John"
        for a in audits
    )


@pytest.mark.anyio
async def test_tool_get_cascade_impact(mcp_server: SupplyChainOSMCPServer):
    """Test 9: get_cascade_impact tool computes 2nd-order fleet and carrier ripple effects."""

    disruptions = await mcp_server.client._request(
        "GET",
        "/disruptions",
    )

    assert isinstance(disruptions, list)
    assert len(disruptions) > 0

    disruption_id = disruptions[0]["id"]

    res = await mcp_server.call_tool(
        "get_cascade_impact",
        {"disruption_id": disruption_id},
    )

    assert res["status"] == "success"

    content = res["content"]

    assert content["disruption_id"] == disruption_id
    assert "direct_count" in content
    assert "secondary_count" in content
    assert "cascade_chain" in content


# ── 4. JSON-RPC 2.0 Protocol Compliance Tests ─────────────────────────────────


@pytest.mark.anyio
async def test_jsonrpc_initialize(mcp_server: SupplyChainOSMCPServer):
    """Verify standard MCP initialize request."""

    req = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "initialize",
        "params": {
            "clientInfo": {
                "name": "BobCopilot",
                "version": "1.0.0",
            }
        },
    }

    resp = await mcp_server.handle_jsonrpc(req)

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == "1"
    assert resp["result"]["serverInfo"]["name"] == "supplychainos-mcp-server"


@pytest.mark.anyio
async def test_jsonrpc_tools_list(mcp_server: SupplyChainOSMCPServer):
    """Verify tools/list protocol endpoint returns all 9 tools."""

    req = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "tools/list",
    }

    resp = await mcp_server.handle_jsonrpc(req)

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == "2"

    tools = resp["result"]["tools"]

    assert len(tools) == 9

    names = {t["name"] for t in tools}

    assert "analyze_disruption" in names
    assert "approve_recommendation" in names
    assert "simulate_scenario" in names


@pytest.mark.anyio
async def test_jsonrpc_tools_call(mcp_server: SupplyChainOSMCPServer):
    """Verify tools/call protocol endpoint correctly dispatches tool invocations."""

    routes = await mcp_server.client._request(
        "GET",
        "/routes",
    )

    route_id = routes[0]["id"]

    req = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "tools/call",
        "params": {
            "name": "find_alternative_routes",
            "arguments": {
                "route_id": route_id,
            },
        },
    }

    resp = await mcp_server.handle_jsonrpc(req)

    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == "3"

    result = resp["result"]

    assert result["tool"] == "find_alternative_routes"
    assert result["status"] == "success"