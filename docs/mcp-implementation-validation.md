# SupplyChainOS — MCP Implementation & Validation Report

## 1. MCP Architecture

The SupplyChainOS Model Context Protocol (MCP) server implements a secure, stateless JSON-RPC 2.0 adapter that bridges conversational LLM interfaces (**IBM Bob Copilot** / watsonx.ai) with the SupplyChainOS operational backend.

```
┌─────────────────────────────────────────────────────────────┐
│                    User / Bob Copilot                       │
│              (Natural Language LLM Interface)               │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON-RPC 2.0 (stdio / SSE)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  SupplyChainOS MCP Server                   │
│   (Tool Allowlist, Schema Validation, Error Masking Gate)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Authenticated HTTP REST Client
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Service                   │
│  (State Machine, Pure-Python Engines, Audit Logging Layer)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ SQLAlchemy 2.0 ORM
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL 16 Database                    │
└─────────────────────────────────────────────────────────────┘
```

### Architectural Guarantees
- **Zero Direct Database Access**: MCP tools never access PostgreSQL directly and contain no database drivers or credentials.
- **Thin Adapter Pattern**: MCP tools contain zero business logic and delegate 100% of analytical computations to existing FastAPI endpoints and business engines.
- **Engine Purity**: Pure Python engines (`backend/engines/`) have zero protocol dependencies and remain completely untouched.

---

## 2. MCP Tools Specification

The MCP server exposes **9 standard tools**:

1. `analyze_disruption`: Evaluates geographic blast radius, severity, and impacted shipments for an active disruption.
2. `get_shipment_risk`: Retrieves deterministic risk scores, ML delay probabilities, and top contributing risk factors.
3. `check_cold_chain`: Checks IoT sensor telemetry, cumulative excursion duration, max deviation, and biological spoilage risk.
4. `get_fleet_status`: Inspects vehicle availability, idle/overloaded telemetry, and redeployment suggestions.
5. `find_alternative_routes`: Queries and ranks alternative bypass routes avoiding disrupted corridors.
6. `simulate_scenario`: Executes an in-memory Digital Twin what-if scenario simulation without mutating live data.
7. `get_recommendations`: Retrieves system-orchestrated recommendations (reroutes, carrier swaps, expedites, fleet redeployments).
8. `approve_recommendation`: Advances a recommendation through the human-in-the-loop approval state machine with audit sign-off.
9. `get_cascade_impact`: Computes 2nd-order downstream ripple effects across connecting carrier networks and shared fleets.

---

## 3. Tool → API Mapping

| MCP Tool Name | Target FastAPI Endpoint | HTTP Method | Output Data |
|---|---|:---:|---|
| `analyze_disruption` | `/api/v1/disruptions/{disruption_id}/impact` | `GET` | Impacted shipments, severity, delay hours |
| `get_shipment_risk` | `/api/v1/shipments/{shipment_id}/risk` | `GET` | Deterministic, ML predictive, and combined scores |
| `check_cold_chain` | `/api/v1/shipments/{shipment_id}/temperature` | `GET` | Sensor logs, excursion severity, spoilage risk |
| `get_fleet_status` | `/api/v1/fleet/redeployment-suggestions` | `GET` | Fleet utilization, idle/overloaded vehicles, matches |
| `find_alternative_routes` | `/api/v1/routes/{route_id}/alternatives` | `GET` | Available alternative routes ranked by reliability |
| `simulate_scenario` | `/api/v1/simulation/run` | `POST` | In-memory scenario summary, ROI, deltas |
| `get_recommendations` | `/api/v1/recommendations` | `GET` | Filtered recommendation list |
| `approve_recommendation`| `/api/v1/recommendations/{id}/approve` | `POST` | Approved recommendation status & audit confirmation |
| `get_cascade_impact` | `/api/v1/disruptions/{disruption_id}/cascade` | `GET` | Secondary affected shipments & cascade chains |

---

## 4. Input Validation & Schema Enforcement

All tool inputs are validated using Pydantic schemas in `backend/mcp/schemas.py`:
- **UUID Validation**: `disruption_id`, `shipment_id`, `route_id`, and `recommendation_id` must match 36-character standard UUID format.
- **Geographic Constraints**: `epicenter_lat` constrained to `[-90, +90]`, `epicenter_lng` constrained to `[-180, +180]`, and `affected_radius_km` constrained to `(0, 10000]`.
- **String Sanitization**: Empty or whitespace-only strings are rejected.

---

## 5. Security Controls

- **Explicit Tool Allowlist**: Only tools in `ALLOWED_TOOLS` frozenset can be executed. Unregistered or hallucinated tool names return standard JSON-RPC error code `-32601`.
- **SQL / Command Injection Defense**: Parameter strings are scanned for SQL injection patterns and rejected at the protocol gateway.
- **Credential & Error Masking**: Exception handlers mask database connection strings, passwords, and internal file paths before returning JSON-RPC error responses.
- **No Direct DB Access**: MCP modules contain no SQLAlchemy Session, engine, or ORM model imports.

---

## 6. Approval Protection & State Machine

- **Mandatory Human Sign-Off**: `approve_recommendation` requires a valid human `actor` name (minimum 2 characters). Anonymous, empty, or automated approvals are rejected.
- **Approval State Machine Preservation**: Invocations route through FastAPI's state machine (`POST /api/v1/recommendations/{id}/approve`), which strictly enforces that only `pending` recommendations can be approved, preventing illegal state transitions.

---

## 7. Audit Behavior

- Every approval or rejection executed via MCP generates an immutable audit record in PostgreSQL `audit_logs` containing:
  - `entity_type`: `"recommendation"`
  - `action`: `"rec_approved"`
  - `actor`: Officer ID supplied via MCP
  - `actor_type`: `"human"`
  - `reasoning`: Operational justification notes
  - `previous_state` & `new_state`: Complete state transition diffs
- Digital Twin simulations executed via `simulate_scenario` write a single `simulation_run` audit record while ensuring **zero operational data rows are modified**.

---

## 8. Test Results

- Test File: `backend/tests/test_mcp.py` (23 dedicated MCP tests)
- Full Test Suite: `pytest backend/tests/ -v`
- **Total Tests**: **173 passed** (100% pass rate)
- Verified Behaviors:
  - Tool allowlist completeness and rejection of unauthorized tools
  - Pydantic schema validation for all 9 tools
  - Rejection of invalid UUIDs, out-of-bound coordinates, and empty fields
  - Correct API client mapping for all endpoints
  - Approval state machine enforcement & audit trail generation
  - Digital Twin in-memory operational isolation
  - JSON-RPC 2.0 protocol endpoints (`initialize`, `tools/list`, `tools/call`)

---

## 9. Known Limitations

1. **Transport Modes**: The MCP server is implemented as a standard Python service supporting in-process, JSON-RPC, and async HTTP transport. Stdio / SSE daemon wrappers can be launched using the standard entrypoint.
2. **Read-Only Digital Twin**: The `simulate_scenario` tool deliberately produces read-only scenario results; it does not persist temporary disruption records to the operational database.
