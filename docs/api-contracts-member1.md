# SupplyChainOS — Backend API Specification & Delivery Guide
**Author / Backend Gateway Lead:** Member 2  
**Target / Recipient:** Member 1 (AI & Copilot Layer / FastMCP Server)  
**Status:** Completed & Tested (279/279 test suites passing)  
**Version:** 1.0.0

---

## 1. Quick Start & Server Setup

### 1.1 Local Run Instructions
To boot the FastAPI server locally on your development machine:

```powershell
# From the repository root
$env:PYTHONPATH="src"
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 1.2 Access & Interactive Docs
- **Base URL:** `http://localhost:8000/api/v1`
- **Interactive Swagger UI (OpenAPI):** `http://localhost:8000/docs`
- **ReDoc Interactive Documentation:** `http://localhost:8000/redoc`
- **OpenAPI JSON Schema:** `http://localhost:8000/openapi.json`
- **Health Check:** `GET http://localhost:8000/api/v1/health`

### 1.3 Recommended MCP Environment Configuration
In your MCP server environment (e.g. `.env` or `server.py`):
```env
BACKEND_API_URL=http://localhost:8000/api/v1
```

---

## 2. MCP Tools to REST Endpoints Mapping

| MCP Tool Name (`src/backend/mcp/tools/`) | HTTP Method | REST Endpoint | Primary Purpose |
| :--- | :--- | :--- | :--- |
| `get_shipment_details` | `GET` | `/api/v1/shipments/{id}` | Telemetry, origin, destination, carrier, route, status |
| `get_shipment_risk` | `GET` | `/api/v1/shipments/{id}/risk` | Operational heuristic & combined multi-factor risk score |
| `get_shipment_prediction` | `GET` | `/api/v1/shipments/{id}/prediction` | Random Forest ML delay probability & delay hours |
| `check_cold_chain_status` | `GET` | `/api/v1/shipments/{id}/cold-chain` | Excursion history, severity, and spoilage risk % |
| `list_active_disruptions` | `GET` | `/api/v1/disruptions` | Active weather, port congestion, strike events |
| `get_disruption_impact` | `GET` | `/api/v1/disruptions/{id}/impact` | Impact radius & affected shipment count |
| `get_fleet_recommendations` | `GET` | `/api/v1/fleet/intelligence` | Available, idle, & redeployment candidates |
| `simulate_what_if_route` | `POST` | `/api/v1/simulations/route` | Digital twin simulation (baseline vs candidate) |
| `simulate_scenario` | `POST` | `/api/v1/simulations/scenario` | Blast-radius disruption what-if scenario |
| `generate_recommendations` | `POST` | `/api/v1/recommendations/generate` | Autonomous multi-engine recommendation synthesis |
| `approve_recommendation` | `POST` | `/api/v1/recommendations/{id}/approve` | HITL approval with DecisionAudit log |
| `reject_recommendation` | `POST` | `/api/v1/recommendations/{id}/reject` | Rejection with reason notes & DecisionAudit log |

---

## 3. Detailed Endpoint Contracts

### 3.1 Shipments & Risk Intelligence

#### A. Get Shipment Details
- **Endpoint:** `GET /api/v1/shipments/{shipment_id}`
- **Response (200 OK):**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "tracking_number": "TRK-PHARMA-2026-001",
  "origin": "Hamburg",
  "destination": "Frankfurt",
  "origin_lat": 53.5511,
  "origin_lng": 9.9937,
  "destination_lat": 50.1109,
  "destination_lng": 8.6821,
  "current_location": "Kassel Junction",
  "current_lat": 51.3127,
  "current_lng": 9.4797,
  "status": "at_risk",
  "cargo_type": "temperature_sensitive",
  "cargo_value_usd": 185000.0,
  "weight_kg": 4200.0,
  "temperature_required": true,
  "temp_min_c": 2.0,
  "temp_max_c": 8.0,
  "risk_score": 78.5,
  "risk_level": "high",
  "carrier": {
    "id": "c0a80121-7ac0-4e31-8930-cf2849b25121",
    "name": "Apex Global Freight",
    "code": "APEX",
    "reliability_score": 0.94
  },
  "route": {
    "id": "d0a80121-7ac0-4e31-8930-cf2849b25132",
    "code": "RT-01",
    "name": "Hamburg to Frankfurt Road Express",
    "distance_km": 492.0
  }
}
```

#### B. Get Operational Risk Score
- **Endpoint:** `GET /api/v1/shipments/{shipment_id}/risk`
- **Response (200 OK):**
```json
{
  "shipment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "risk_score": 78.5,
  "risk_level": "high",
  "is_high_risk": true,
  "factors": [
    "Carrier reliability (94%) is acceptable",
    "Active disruption within 85.0km of route corridor",
    "Temperature excursion detected in sensor telemetry"
  ],
  "components": {
    "route_risk": 35.0,
    "carrier_risk": 6.0,
    "disruption_risk": 37.5
  }
}
```

#### C. Get ML Delay Prediction
- **Endpoint:** `GET /api/v1/shipments/{shipment_id}/prediction`
- **Response (200 OK):**
```json
{
  "shipment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "delay_probability": 0.82,
  "delay_risk_score": 82.0,
  "predicted_delay_hours": 8.5,
  "model_version": "RandomForest_v1.0",
  "available": true
}
```

#### D. Check Cold Chain Sensor Telemetry
- **Endpoint:** `GET /api/v1/shipments/{shipment_id}/cold-chain`
- **Response (200 OK):**
```json
{
  "shipment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "has_excursion": true,
  "excursion_severity": "CRITICAL",
  "max_temp_reached": 11.4,
  "min_temp_reached": 4.1,
  "excursion_duration_mins": 45.0,
  "spoilage_risk_percent": 68.5,
  "excursions": [
    {
      "start_time": "2026-09-14T10:00:00Z",
      "end_time": "2026-09-14T10:45:00Z",
      "duration_mins": 45.0,
      "max_deviation_c": 3.4,
      "severity": "CRITICAL",
      "reading_count": 9
    }
  ],
  "factors": [
    "Temperature excursion of 3.4°C above maximum limit",
    "Cumulative excursion duration: 45.0 minutes"
  ]
}
```

---

### 3.2 Disruptions & Blast Radius

#### A. List Active Disruptions
- **Endpoint:** `GET /api/v1/disruptions?status=active`
- **Query Params:** `status` (optional: `active`, `pending`, `resolved`), `severity` (optional)
- **Response (200 OK):** Array of disruption objects.

#### B. Get Disruption Impact
- **Endpoint:** `GET /api/v1/disruptions/{disruption_id}/impact`
- **Response (200 OK):**
```json
{
  "disruption_id": "e0a80121-7ac0-4e31-8930-cf2849b25143",
  "title": "North Sea Winter Gale",
  "severity": "critical",
  "affected_radius_km": 250.0,
  "total_shipments_evaluated": 12,
  "affected_shipments_count": 3,
  "affected_shipments": [
    {
      "shipment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "tracking_number": "TRK-PHARMA-2026-001",
      "status": "at_risk",
      "distance_to_epicenter_km": 85.2,
      "estimated_delay_hours": 14.0
    }
  ]
}
```

---

### 3.3 Fleet Intelligence

#### A. Fleet Intelligence & Candidate Search
- **Endpoint:** `GET /api/v1/fleet/intelligence`
- **Query Params (Optional for geo-matching):**
  - `epicenter_lat` (float)
  - `epicenter_lng` (float)
  - `required_capacity` (float, tons)
  - `requires_reefer` (bool)
- **Response (200 OK):**
```json
{
  "summary": {
    "total_vehicles": 6,
    "idle_count": 1,
    "available_count": 2,
    "overloaded_count": 1,
    "in_transit_count": 2,
    "maintenance_count": 0,
    "average_utilisation_percent": 54.2,
    "refrigerated_available": 1
  },
  "idle_vehicles": [...],
  "available_vehicles": [...],
  "overloaded_vehicles": [...],
  "redeployment_candidates": [
    {
      "id": "f0a80121-7ac0-4e31-8930-cf2849b25154",
      "vehicle_code": "FL-TRK-103",
      "vehicle_type": "reefer_truck",
      "capacity_tons": 20.0,
      "current_load_tons": 2.0,
      "utilisation_percent": 10.0,
      "is_refrigerated": true,
      "status": "available",
      "distance_km": 12.4,
      "suitability_score": 92.5
    }
  ],
  "factors": [
    "1 refrigerated vehicle(s) currently available near depot",
    "Vehicle FL-TRK-103 has 18.0 tons spare capacity"
  ]
}
```

---

### 3.4 What-If Simulations (Digital Twin)

#### A. Simulate Route & Carrier Switch
- **Endpoint:** `POST /api/v1/simulations/route`
- **Request Body:**
```json
{
  "shipment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "candidate_route_id": "d0a80121-7ac0-4e31-8930-cf2849b25132",
  "candidate_carrier_id": "c0a80121-7ac0-4e31-8930-cf2849b25121"
}
```
- **Response (200 OK):**
```json
{
  "shipment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "baseline": {
    "total_delay_hours": 36.0,
    "total_cost_usd": 12500.0,
    "risk_score": 82.0
  },
  "simulated": {
    "total_delay_hours": 6.5,
    "total_cost_usd": 14200.0,
    "risk_score": 24.0
  },
  "delta": {
    "delay_reduction_hours": 29.5,
    "cost_variance_usd": 1700.0,
    "risk_reduction_score": 58.0
  },
  "business_impact": {
    "roi_factor": 4.2,
    "spoiled_cargo_prevented_usd": 185000.0
  }
}
```

---

### 3.5 Recommendations & Human-in-the-Loop (HITL)

#### A. Generate Recommendations
- **Endpoint:** `POST /api/v1/recommendations/generate?shipment_id={optional_uuid}`
- **Description:** Synthesizes outputs from all 10 intelligence engines into actionable recommendations saved to the database.
- **Response (200 OK):**
```json
{
  "status": "ok",
  "generated_count": 1,
  "recommendations": [
    {
      "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "shipment_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "type": "reroute",
      "priority": "critical",
      "title": "Reroute — TRK-PHARMA-2026-001",
      "status": "pending"
    }
  ]
}
```

#### B. Approve Recommendation (HITL)
- **Endpoint:** `POST /api/v1/recommendations/{recommendation_id}/approve`
- **Request Body:**
```json
{
  "actor": "IBM Bob Copilot",
  "notes": "Approved alternative route RT-01 avoiding North Sea gale"
}
```
- **Response (200 OK):** Returns the full `RecommendationRead` object with `status: "approved"`, `approved_by`, `approved_at`, and automatically creates a tamper-proof audit trail record in `decision_audit`.

#### C. Reject Recommendation
- **Endpoint:** `POST /api/v1/recommendations/{recommendation_id}/reject`
- **Request Body:**
```json
{
  "actor": "Lead Logistics Officer",
  "notes": "Cost variance exceeds threshold"
}
```
- **Response (200 OK):** Returns updated recommendation with `status: "rejected"` and logs audit record.

---

### 3.6 Decision Audit Trail
- **Endpoint:** `GET /api/v1/audit?limit=50&offset=0`
- **Query Params:** `entity_type` (optional), `entity_id` (optional), `actor` (optional), `limit`, `offset`
- **Response (200 OK):** Chronological log of human-in-the-loop decisions, rationale, previous state, and new state.

---

## 4. Example MCP Tool Client Implementation (Python `httpx`)

Here is how your MCP tools can cleanly query the backend:

```python
import os
import httpx

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")

async def check_cold_chain_status(shipment_id: str) -> dict:
    url = f"{BACKEND_API_URL}/shipments/{shipment_id}/cold-chain"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()

async def simulate_what_if_route(shipment_id: str, candidate_route_id: str, candidate_carrier_id: str) -> dict:
    url = f"{BACKEND_API_URL}/simulations/route"
    payload = {
        "shipment_id": shipment_id,
        "candidate_route_id": candidate_route_id,
        "candidate_carrier_id": candidate_carrier_id
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

async def approve_recommendation(recommendation_id: str, actor: str, notes: str) -> dict:
    url = f"{BACKEND_API_URL}/recommendations/{recommendation_id}/approve"
    payload = {"actor": actor, "notes": notes}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
```
