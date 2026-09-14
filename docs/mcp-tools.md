# SupplyChainOS — Model Context Protocol (MCP) Tool Specifications

> **Document Version**: 1.0.0  
> **Status**: 📋 PLANNED (Specification & Tool Schema Contract)  
> **Author**: Member 1 — Enterprise Software Architect  
> **Target Audience**: AI Developers, Backend Engineers, Tool Integrators, Bob Copilot Developers  

---

## 1. Overview & Tool Classification

The Model Context Protocol (MCP) server for SupplyChainOS exposes a suite of deterministic, sandboxed tools enabling conversational AI assistants (such as **Bob Copilot** / IBM watsonx.ai) to inspect live supply chain state, evaluate risks, simulate what-if scenarios, and request operator approvals.

### Classification Matrix

| Tool Name | Class | Purpose | Target Endpoint | Status |
|---|---|---|---|:---:|
| `analyze_disruption` | 👁️ **READ** | Evaluate geographic & route impact of a disruption | `GET /api/v1/disruptions/{id}/impact` | ✅ Backend Implemented / MCP Planned |
| `get_shipment_status` | 👁️ **READ** | Retrieve live telemetry and shipment status | `GET /api/v1/shipments/{id}` | ✅ Backend Implemented / MCP Planned |
| `get_shipment_risk` | 👁️ **READ** | Recalculate deterministic + ML predictive risk | `GET /api/v1/shipments/{id}/risk` | ✅ Backend Implemented / MCP Planned |
| `check_cold_chain` | 👁️ **READ** | Inspect sensor logs & detect temperature excursions | `GET /api/v1/shipments/{id}/temperature` | ✅ Backend Implemented / MCP Planned |
| `get_fleet_status` | 👁️ **READ** | Inspect idle/overloaded fleet and redeployment options | `GET /api/v1/fleet` | ✅ Backend Implemented / MCP Planned |
| `find_alternative_routes` | 👁️ **READ** | Query alternative routes for an origin/destination | `GET /api/v1/routes/{id}/alternatives` | ✅ Backend Implemented / MCP Planned |
| `get_recommendations` | 👁️ **READ** | Fetch system-generated mitigation recommendations | `GET /api/v1/recommendations` | ✅ Backend Implemented / MCP Planned |
| `get_business_impact` | 👁️ **READ** | Calculate financial exposure and SLA breach risk | `GET /api/v1/disruptions/{id}/impact` (or engine direct) | ✅ Backend Implemented / MCP Planned |
| `get_cascade_impact` | 👁️ **READ** | Analyze 1st-order fleet and carrier ripple effects | `GET /api/v1/disruptions/{id}/cascade` | ✅ Backend Implemented / MCP Planned |
| `simulate_scenario` | 🧪 **SIMULATION** | Run in-memory Digital Twin what-if simulation | `POST /api/v1/simulation/run` | ✅ Backend Implemented / MCP Planned |
| `approve_recommendation`| ✍️ **WRITE/APPROVAL** | Execute human approval state machine transition | `POST /api/v1/recommendations/{id}/approve` | ✅ Backend Implemented / MCP Planned |

> [!IMPORTANT]
> **Implementation Note**: The underlying FastAPI endpoints and pure-Python engines for all 11 tools are **✅ IMPLEMENTED** and verified with 146 unit tests. The MCP JSON-RPC protocol wrapper layer is **📋 PLANNED**.

---

## 2. Detailed Tool Specifications

```
  ┌─────────────────────────────────────────────────────────────┐
  │                        READ TOOLS                           │
  │  (Idempotent, Zero DB Mutations, No Human Approvals Needed) │
  └─────────────────────────────────────────────────────────────┘
```

### 1. `analyze_disruption`
- **Purpose**: Calculate which active shipments intersect a disruption's geographic epicenter or have routes blocked by it.
- **User Intent**: *"Which shipments are affected by disruption DISP-101?"* / *"Show me the impact of the Red Sea security event."*
- **Classification**: 👁️ **READ**
- **Input Parameters**:
  - `disruption_id` (string, required): UUID of the disruption to analyze.
- **Input Validation**:
  - Valid UUIDv4 format required.
- **Output Structure**:
  - `disruption_id`: string (UUID)
  - `affected_count`: integer
  - `impacted_shipments`: list of objects containing `shipment_id`, `impact_reason` (`geo_intersection` | `route_blocked` | `both`), `distance_to_epicenter_km`, `impact_score` (0-100), `impact_level` (`LOW` | `MEDIUM` | `HIGH` | `CRITICAL`), `estimated_delay_hours`, and `factors` (list of strings).
- **API Endpoint Mapping**: `GET /api/v1/disruptions/{disruption_id}/impact` (✅ IMPLEMENTED)
- **Engine(s) Involved**: `DisruptionImpactEngine`
- **Permission Requirement**: `operator:read`
- **Human Approval Requirement**: ❌ None
- **Audit Requirement**: ❌ None (Read-only query)
- **Error Cases**:
  - `404 Not Found`: Disruption ID does not exist in the database.
  - `422 Unprocessable Entity`: Malformed UUID string.
- **Example Request**:
```json
{
  "name": "analyze_disruption",
  "arguments": {
    "disruption_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  }
}
```
- **Example Response**:
```json
{
  "disruption_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "affected_count": 2,
  "impacted_shipments": [
    {
      "shipment_id": "e4eaaaf2-d142-11e1-b3e4-080027620cdd",
      "impact_reason": "both",
      "distance_to_epicenter_km": 42.5,
      "impact_score": 85,
      "impact_level": "CRITICAL",
      "estimated_delay_hours": 36.0,
      "factors": [
        "Critical severity disruption (+60)",
        "Shipment intersects disruption area and route is directly blocked (+20)",
        "Shipment is within 50 km of disruption (+10)"
      ]
    }
  ]
}
```

---

### 2. `get_shipment_status`
- **Purpose**: Fetch real-time telemetry, coordinates, cargo details, current carrier, route, and ETA for a specific shipment.
- **User Intent**: *"Where is shipment TRK-1002 right now?"* / *"What is the status of shipment shp-001?"*
- **Classification**: 👁️ **READ**
- **Input Parameters**:
  - `shipment_id` (string, required): UUID of the shipment.
- **Input Validation**:
  - Valid UUIDv4 format required.
- **Output Structure**:
  - `id`: string (UUID)
  - `tracking_number`: string
  - `status`: string (`in_transit`, `delayed`, `at_risk`, `delivered`, `pending`, `cancelled`)
  - `origin`: string
  - `destination`: string
  - `current_lat`: float
  - `current_lng`: float
  - `cargo_type`: string
  - `cargo_value_usd`: float
  - `temperature_required`: boolean
  - `carrier_id`: string (UUID)
  - `route_id`: string (UUID)
  - `scheduled_arrival`: string (ISO 8601)
  - `estimated_arrival`: string (ISO 8601)
  - `risk_level`: string (`low`, `medium`, `high`, `critical`)
- **API Endpoint Mapping**: `GET /api/v1/shipments/{shipment_id}` (✅ IMPLEMENTED)
- **Engine(s) Involved**: None (Direct database ORM query)
- **Permission Requirement**: `operator:read`
- **Human Approval Requirement**: ❌ None
- **Audit Requirement**: ❌ None
- **Error Cases**:
  - `404 Not Found`: Shipment ID does not exist.
  - `422 Unprocessable Entity`: Invalid UUID format.
- **Example Request**:
```json
{
  "name": "get_shipment_status",
  "arguments": {
    "shipment_id": "e4eaaaf2-d142-11e1-b3e4-080027620cdd"
  }
}
```
- **Example Response**:
```json
{
  "id": "e4eaaaf2-d142-11e1-b3e4-080027620cdd",
  "tracking_number": "TRK-1002",
  "status": "at_risk",
  "origin": "Shanghai",
  "destination": "Rotterdam",
  "current_lat": 15.2,
  "current_lng": 41.8,
  "cargo_type": "temperature_sensitive",
  "cargo_value_usd": 120000.0,
  "temperature_required": true,
  "carrier_id": "c1111111-1111-1111-1111-111111111111",
  "route_id": "r1111111-1111-1111-1111-111111111111",
  "scheduled_arrival": "2026-09-18T12:00:00Z",
  "estimated_arrival": "2026-09-20T08:00:00Z",
  "risk_level": "high"
}
```

---

### 3. `get_shipment_risk`
- **Purpose**: Recalculate deterministic rule-based and ML predictive risk scores for a shipment, returning explainable factor breakdowns.
- **User Intent**: *"Why is shipment TRK-1002 marked as high risk?"* / *"Calculate delay probability for shipment shp-001."*
- **Classification**: 👁️ **READ**
- **Input Parameters**:
  - `shipment_id` (string, required): UUID of the shipment.
- **Input Validation**:
  - Valid UUIDv4 format required.
- **Output Structure**:
  - `shipment_id`: string (UUID)
  - `deterministic_score`: float [0.0 - 1.0]
  - `ml_score`: float | null [0.0 - 1.0]
  - `combined_score`: float [0.0 - 1.0] (0.6 * det + 0.4 * ml)
  - `risk_level`: string (`low`, `medium`, `high`, `critical`)
  - `explanation`: string
  - `factors`: list of objects (`name`, `value`, `contribution`)
  - `ml_top_features`: list of objects (`feature`, `value`, `importance`)
  - `model_version`: string
- **API Endpoint Mapping**: `GET /api/v1/shipments/{shipment_id}/risk` (✅ IMPLEMENTED)
- **Engine(s) Involved**: `ShipmentRiskEngine`, `PredictiveRiskEngine`
- **Permission Requirement**: `operator:read`
- **Human Approval Requirement**: ❌ None
- **Audit Requirement**: ✅ System Audit (Logs calculation event in `audit_logs`)
- **Error Cases**:
  - `404 Not Found`: Shipment ID does not exist.
  - `500 Server Error`: Predictive model artifact corrupted or unreadable.
- **Example Request**:
```json
{
  "name": "get_shipment_risk",
  "arguments": {
    "shipment_id": "e4eaaaf2-d142-11e1-b3e4-080027620cdd"
  }
}
```
- **Example Response**:
```json
{
  "shipment_id": "e4eaaaf2-d142-11e1-b3e4-080027620cdd",
  "deterministic_score": 0.72,
  "ml_score": 0.785,
  "combined_score": 0.746,
  "risk_level": "high",
  "explanation": "High risk due to 1 critical disruption, tight 18h arrival buffer, and low carrier reliability.",
  "factors": [
    { "name": "disruption_severity", "value": "critical", "contribution": 0.30 },
    { "name": "arrival_urgency", "value": "<24h", "contribution": 0.12 }
  ],
  "ml_top_features": [
    { "feature": "days_to_scheduled_arrival", "value": 0.75, "importance": 0.32 },
    { "feature": "worst_disruption_severity_encoded", "value": 4.0, "importance": 0.28 }
  ],
  "model_version": "1.0.0"
}
```

---

### 4. `check_cold_chain`
- **Purpose**: Analyze temperature log history for a cold-chain shipment to detect threshold excursions and assess spoilage risk.
- **User Intent**: *"Did shipment TRK-1002 suffer any temperature excursions?"* / *"Check cold-chain integrity for vaccine shipment."*
- **Classification**: 👁️ **READ**
- **Input Parameters**:
  - `shipment_id` (string, required): UUID of the shipment.
- **Input Validation**:
  - Valid UUIDv4 format required.
- **Output Structure**:
  - `shipment_id`: string (UUID)
  - `temperature_required`: boolean
  - `temp_min_c`: float | null
  - `temp_max_c`: float | null
  - `log_count`: integer
  - `analysis`: object | null (`has_excursion`, `severity`, `excursion_count`, `max_deviation_c`, `total_excursion_minutes`, `recommended_action`, `explanation`)
- **API Endpoint Mapping**: `GET /api/v1/shipments/{shipment_id}/temperature` (✅ IMPLEMENTED)
- **Engine(s) Involved**: `ColdChainAnomalyEngine`
- **Permission Requirement**: `operator:read`
- **Human Approval Requirement**: ❌ None
- **Audit Requirement**: ❌ None
- **Error Cases**:
  - `404 Not Found`: Shipment ID does not exist.
  - Returns `analysis: null` if `temperature_required` is `false`.
- **Example Request**:
```json
{
  "name": "check_cold_chain",
  "arguments": {
    "shipment_id": "e4eaaaf2-d142-11e1-b3e4-080027620cdd"
  }
}
```
- **Example Response**:
```json
{
  "shipment_id": "e4eaaaf2-d142-11e1-b3e4-080027620cdd",
  "temperature_required": true,
  "temp_min_c": 2.0,
  "temp_max_c": 8.0,
  "log_count": 24,
  "analysis": {
    "has_excursion": true,
    "severity": "CRITICAL",
    "excursion_count": 2,
    "max_deviation_c": 4.5,
    "total_excursion_minutes": 180,
    "recommended_action": "EXPEDITE_IMMEDIATELY",
    "explanation": "Temperature exceeded 8.0°C for 180 minutes (peak 12.5°C). Critical biological spoilage risk."
  }
}
```

---

### 5. `get_fleet_status`
- **Purpose**: Query fleet asset distribution, filtering for idle (<20% utilization) or overloaded (>95% utilization) vehicles, and generate redeployment recommendations.
- **User Intent**: *"Show me all idle refrigerated trucks near the Red Sea."* / *"What is our current fleet utilization?"*
- **Classification**: 👁️ **READ**
- **Input Parameters**:
  - `status_filter` (string, optional, enum: `all`, `idle`, `overloaded`, default: `all`)
- **Input Validation**:
  - Value must match enum options if provided.
- **Output Structure**:
  - `vehicles`: list of objects containing `id`, `vehicle_id`, `type`, `status`, `capacity_kg`, `current_lat`, `current_lng`, `utilization_pct`, `temperature_capable`, `carrier_id`.
  - `total_count`: integer
- **API Endpoint Mapping**: `GET /api/v1/fleet`, `GET /api/v1/fleet/idle`, `GET /api/v1/fleet/overloaded` (✅ IMPLEMENTED)
- **Engine(s) Involved**: `FleetIntelligenceEngine`
- **Permission Requirement**: `operator:read`
- **Human Approval Requirement**: ❌ None
- **Audit Requirement**: ❌ None
- **Error Cases**:
  - `400 Bad Request`: Invalid status filter supplied.
- **Example Request**:
```json
{
  "name": "get_fleet_status",
  "arguments": {
    "status_filter": "idle"
  }
}
```
- **Example Response**:
```json
{
  "vehicles": [
    {
      "id": "f1111111-1111-1111-1111-111111111111",
      "vehicle_id": "VH-IDLE-04",
      "type": "refrigerated_truck",
      "status": "active",
      "capacity_kg": 12000.0,
      "current_lat": 15.4,
      "current_lng": 42.1,
      "utilization_pct": 12.5,
      "temperature_capable": true,
      "carrier_id": "c1111111-1111-1111-1111-111111111111"
    }
  ],
  "total_count": 1
}
```

---

### 6. `find_alternative_routes`
- **Purpose**: Search for viable alternative transport routes matching origin and destination pairs while avoiding active disruptions.
- **User Intent**: *"What alternative routes are available for the Shanghai-to-Rotterdam corridor?"*
- **Classification**: 👁️ **READ**
- **Input Parameters**:
  - `route_id` (string, required): UUID of the current route.
- **Input Validation**:
  - Valid UUIDv4 format required.
- **Output Structure**:
  - `current_route_id`: string (UUID)
  - `alternatives`: list of objects containing `id`, `code`, `name`, `mode`, `origin`, `destination`, `distance_km`, `typical_duration_hours`, `cost_per_kg_usd`, `reliability_score`, `active`.
- **API Endpoint Mapping**: `GET /api/v1/routes/{route_id}/alternatives` (✅ IMPLEMENTED)
- **Engine(s) Involved**: `RouteOptimizationEngine` / Database Reference Query
- **Permission Requirement**: `operator:read`
- **Human Approval Requirement**: ❌ None
- **Audit Requirement**: ❌ None
- **Error Cases**:
  - `404 Not Found`: Route ID does not exist.
- **Example Request**:
```json
{
  "name": "find_alternative_routes",
  "arguments": {
    "route_id": "r1111111-1111-1111-1111-111111111111"
  }
}
```
- **Example Response**:
```json
{
  "current_route_id": "r1111111-1111-1111-1111-111111111111",
  "alternatives": [
    {
      "id": "r2222222-2222-2222-2222-222222222222",
      "code": "RT-CAPE",
      "name": "Cape of Good Hope Route",
      "mode": "sea",
      "origin": "Shanghai",
      "destination": "Rotterdam",
      "distance_km": 15200.0,
      "typical_duration_hours": 96.0,
      "cost_per_kg_usd": 1.25,
      "reliability_score": 0.92,
      "active": true
    }
  ]
}
```

---

### 7. `get_recommendations`
- **Purpose**: Query system-generated AI recommendations, filtering by status, priority, or disruption ID.
- **User Intent**: *"What recommendations are currently pending approval?"* / *"Show recommendations for disruption DISP-101."*
- **Classification**: 👁️ **READ**
- **Input Parameters**:
  - `status` (string, optional, enum: `pending`, `approved`, `rejected`, `deferred`, `implemented`)
  - `priority` (string, optional, enum: `low`, `medium`, `high`, `critical`)
  - `disruption_id` (string, optional, UUID format)
- **Input Validation**:
  - Enums validated against state machine definitions.
- **Output Structure**:
  - `recommendations`: list of objects containing `id`, `shipment_id`, `disruption_id`, `type` (`reroute`, `carrier_change`, `fleet_redeploy`, `hold`, `expedite`, `escalate`), `priority`, `title`, `description`, `reason`, `estimated_savings_usd`, `estimated_delay_reduction_hours`, `requires_approval`, `status`.
- **API Endpoint Mapping**: `GET /api/v1/recommendations` (✅ IMPLEMENTED)
- **Engine(s) Involved**: `RecommendationEngine`
- **Permission Requirement**: `operator:read`
- **Human Approval Requirement**: ❌ None
- **Audit Requirement**: ❌ None
- **Error Cases**:
  - `400 Bad Request`: Invalid status or priority filter.
- **Example Request**:
```json
{
  "name": "get_recommendations",
  "arguments": {
    "status": "pending",
    "priority": "critical"
  }
}
```
- **Example Response**:
```json
{
  "recommendations": [
    {
      "id": "rec-001",
      "shipment_id": "e4eaaaf2-d142-11e1-b3e4-080027620cdd",
      "disruption_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "type": "expedite",
      "priority": "critical",
      "title": "Expedite TRK-1002 — cold-chain excursion",
      "description": "Temperature excursion detected. Immediate expedited delivery required to preserve cargo integrity.",
      "reason": "Shipment TRK-1002 requires expedited delivery: active temperature excursion detected on temperature-sensitive cargo (cargo value: $120,000).",
      "estimated_savings_usd": 6000.0,
      "estimated_delay_reduction_hours": 0.0,
      "requires_approval": true,
      "status": "pending"
    }
  ]
}
```

---

### 8. `get_business_impact`
- **Purpose**: Calculate total financial exposure, delay costs, and SLA breach penalty risks resulting from a disruption or set of shipments.
- **User Intent**: *"What is the financial cost of this delay?"* / *"How many SLA penalties are we exposed to?"*
- **Classification**: 👁️ **READ**
- **Input Parameters**:
  - `disruption_id` (string, required): UUID of the disruption to calculate impact for.
- **Input Validation**:
  - Valid UUIDv4 format required.
- **Output Structure**:
  - `disruption_id`: string (UUID)
  - `total_cargo_value_at_risk_usd`: float
  - `total_delay_hours`: float
  - `avg_delay_hours`: float
  - `cost_of_delay_usd`: float
  - `penalty_exposure_usd`: float
  - `sla_breach_count`: integer
  - `explanation`: string
- **API Endpoint Mapping**: `GET /api/v1/disruptions/{disruption_id}/impact` (✅ IMPLEMENTED) / `BusinessImpactEngine`
- **Engine(s) Involved**: `BusinessImpactEngine`, `DisruptionImpactEngine`
- **Permission Requirement**: `operator:read`
- **Human Approval Requirement**: ❌ None
- **Audit Requirement**: ❌ None
- **Error Cases**:
  - `404 Not Found`: Disruption ID does not exist.
- **Example Request**:
```json
{
  "name": "get_business_impact",
  "arguments": {
    "disruption_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  }
}
```
- **Example Response**:
```json
{
  "disruption_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "total_cargo_value_at_risk_usd": 240000.0,
  "total_delay_hours": 54.0,
  "avg_delay_hours": 27.0,
  "cost_of_delay_usd": 1080.0,
  "penalty_exposure_usd": 10000.0,
  "sla_breach_count": 2,
  "explanation": "2 shipments affected. Total cargo value at risk: $240,000. Estimated cost of delay: $1,080. SLA breaches: 2 (penalty exposure: $10,000). Avg delay: 27.0h."
}
```

---

### 9. `get_cascade_impact`
- **Purpose**: Perform 1st-order graph cascade analysis to find secondary shipments delayed through shared fleet vehicles or overloaded carrier capacity.
- **User Intent**: *"Are any other shipments going to be delayed because of shared fleet vehicles?"* / *"Check carrier cascade effects."*
- **Classification**: 👁️ **READ**
- **Input Parameters**:
  - `disruption_id` (string, required): UUID of the direct disruption.
- **Input Validation**:
  - Valid UUIDv4 format required.
- **Output Structure**:
  - `disruption_id`: string (UUID)
  - `direct_count`: integer
  - `secondary_count`: integer
  - `total_value_at_risk_usd`: float
  - `total_delay_hours_estimate`: float
  - `explanation`: string
  - `cascade_chain`: list of objects containing `shipment_id`, `tracking_number`, `level`, `impact_type` (`fleet_cascade` | `carrier_cascade`), `caused_by_shipment_id`, `estimated_delay_hours`.
- **API Endpoint Mapping**: `GET /api/v1/disruptions/{disruption_id}/cascade` (✅ IMPLEMENTED)
- **Engine(s) Involved**: `CascadingImpactEngine`
- **Permission Requirement**: `operator:read`
- **Human Approval Requirement**: ❌ None
- **Audit Requirement**: ❌ None
- **Error Cases**:
  - `404 Not Found`: Disruption ID does not exist.
- **Example Request**:
```json
{
  "name": "get_cascade_impact",
  "arguments": {
    "disruption_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  }
}
```
- **Example Response**:
```json
{
  "disruption_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "direct_count": 1,
  "secondary_count": 1,
  "total_value_at_risk_usd": 85000.0,
  "total_delay_hours_estimate": 12.0,
  "explanation": "1 shipments directly affected. 1 secondary shipments identified (1 fleet cascade, 0 carrier cascade). Total secondary cargo value at risk: $85,000.",
  "cascade_chain": [
    {
      "shipment_id": "f8eaaaf2-d142-11e1-b3e4-080027620cee",
      "tracking_number": "TRK-2005",
      "level": 1,
      "impact_type": "fleet_cascade",
      "caused_by_shipment_id": "e4eaaaf2-d142-11e1-b3e4-080027620cdd",
      "estimated_delay_hours": 12.0
    }
  ]
}
```

---

```
  ┌─────────────────────────────────────────────────────────────┐
  │                     SIMULATION TOOLS                        │
  │    (Pure In-Memory Execution, Zero Operational Mutations)   │
  └─────────────────────────────────────────────────────────────┘
```

### 10. `simulate_scenario`
- **Purpose**: Run an in-memory Digital Twin what-if simulation for a hypothetical or extended disruption, evaluating impact, risks, cascade, and generating mitigation recommendations without modifying live operational data.
- **User Intent**: *"What if the port of Singapore closes for 72 hours with a 200km radius?"* / *"Simulate a Category 4 typhoon in the South China Sea."*
- **Classification**: 🧪 **SIMULATION**
- **Input Parameters**:
  - `title` (string, required): Title / name of the what-if scenario.
  - `disruption_type` (string, required, enum: `weather`, `port_congestion`, `geopolitical`, `customs_delay`, `equipment_failure`, `labor_strike`).
  - `disruption_severity` (string, required, enum: `low`, `medium`, `high`, `critical`).
  - `epicenter_lat` (number, required, range: -90.0 to 90.0).
  - `epicenter_lng` (number, required, range: -180.0 to 180.0).
  - `affected_radius_km` (number, required, range: 1.0 to 5000.0).
  - `affected_route_codes` (array of strings, optional, default: `[]`).
  - `shipment_ids` (array of strings, optional, default: null — all active shipments evaluated).
- **Input Validation**:
  - Latitude clamped between `[-90, 90]`, Longitude between `[-180, 180]`, Radius > 0.
- **Output Structure**:
  - `scenario_summary`: object containing `name`, `disruption_type`, `severity`, `affected_radius_km`, `horizon_hours`, `total_affected_shipments`, `total_secondary_shipments`, `total_cargo_value_at_risk_usd`, `total_cost_of_delay_usd`, `penalty_exposure_usd`, `sla_breach_count`, `recommendation_count`.
  - `affected_shipment_count`: integer
  - `risk_scores`: list of objects (`shipment_id`, `combined_risk_score`)
  - `cascade_analysis`: object (`direct_count`, `secondary_count`, `explanation`)
  - `business_impact`: object (`total_cargo_value_at_risk_usd`, `cost_of_delay_usd`, `penalty_exposure_usd`, `sla_breach_count`, `avg_delay_hours`)
  - `top_recommendations`: list of serialized recommendation dictionaries.
- **API Endpoint Mapping**: `POST /api/v1/simulation/run` (✅ IMPLEMENTED)
- **Engine(s) Involved**: `DigitalTwinEngine`, `DisruptionImpactEngine`, `ShipmentRiskEngine`, `PredictiveRiskEngine`, `RouteOptimizationEngine`, `CarrierRecommendationEngine`, `CascadingImpactEngine`, `BusinessImpactEngine`, `RecommendationEngine`
- **Permission Requirement**: `operator:simulate`
- **Human Approval Requirement**: ❌ None (Simulation is strictly in-memory)
- **Audit Requirement**: ✅ Simulation Audit (One audit record written with scenario metadata for traceability)
- **Error Cases**:
  - `422 Unprocessable Entity`: Coordinate out of range or missing required parameters.
- **Example Request**:
```json
{
  "name": "simulate_scenario",
  "arguments": {
    "title": "What-If: Typhoon Malakas in Hong Kong",
    "disruption_type": "weather",
    "disruption_severity": "critical",
    "epicenter_lat": 22.3,
    "epicenter_lng": 114.2,
    "affected_radius_km": 350.0,
    "affected_route_codes": ["RT-HK-SGP"]
  }
}
```
- **Example Response**:
```json
{
  "scenario_summary": {
    "name": "What-If: Typhoon Malakas in Hong Kong",
    "disruption_type": "weather",
    "severity": "critical",
    "affected_radius_km": 350.0,
    "horizon_hours": 72.0,
    "total_affected_shipments": 4,
    "total_secondary_shipments": 1,
    "total_cargo_value_at_risk_usd": 680000.0,
    "total_cost_of_delay_usd": 8500.0,
    "penalty_exposure_usd": 15000.0,
    "sla_breach_count": 3,
    "recommendation_count": 6
  },
  "affected_shipment_count": 4,
  "top_recommendations": [
    {
      "type": "reroute",
      "priority": "critical",
      "title": "Reroute TRK-1002 via RT-PACIFIC",
      "reason": "Shipment TRK-1002 is rerouted via RT-PACIFIC because current route is affected by 'What-If: Typhoon Malakas'.",
      "requires_approval": true,
      "estimated_savings_usd": 3400.0
    }
  ]
}
```

---

```
  ┌─────────────────────────────────────────────────────────────┐
  │                    WRITE / APPROVAL TOOLS                   │
  │     (State Machine Mutations, Strict Human Actor Required)  │
  └─────────────────────────────────────────────────────────────┘
```

### 11. `approve_recommendation`
- **Purpose**: Transition a pending recommendation to `approved` state in the recommendation state machine and commit an immutable audit record.
- **User Intent**: *"Approve recommendation rec-001 with reason: Approved per risk protocol."*
- **Classification**: ✍️ **WRITE / APPROVAL**
- **Input Parameters**:
  - `recommendation_id` (string, required): UUID of the recommendation.
  - `approved_by` (string, required): Username or employee ID of the human approver.
  - `reason` (string, required): Justification note for the audit log.
- **Input Validation**:
  - `recommendation_id` must be a valid UUIDv4.
  - `approved_by` must not be empty or `"system"`.
  - `reason` must not be empty (minimum 5 characters).
- **Output Structure**:
  - `id`: string (UUID)
  - `status`: string (`approved`)
  - `approved_by`: string
  - `approved_at`: string (ISO 8601)
  - `title`: string
  - `reason`: string
  - `updated_at`: string (ISO 8601)
- **API Endpoint Mapping**: `POST /api/v1/recommendations/{rec_id}/approve` (✅ IMPLEMENTED)
- **Engine(s) Involved**: Recommendation State Machine, `write_audit`
- **Permission Requirement**: `supervisor:approve`
- **Human Approval Requirement**: ✅ Mandatory (Requires human operator identity)
- **Audit Requirement**: ✅ Mandatory Audit Trail (Action `rec_approved` logged with actor, previous state, new state, and reasoning)
- **Error Cases**:
  - `404 Not Found`: Recommendation ID does not exist.
  - `400 Bad Request`: Recommendation is not in `pending` state (invalid transition).
  - `422 Unprocessable Entity`: Empty `approved_by` or missing `reason`.
- **Example Request**:
```json
{
  "name": "approve_recommendation",
  "arguments": {
    "recommendation_id": "a1111111-1111-1111-1111-111111111111",
    "approved_by": "supervisor.sarah",
    "reason": "Approved reroute via Cape of Good Hope to avoid Red Sea security risks."
  }
}
```
- **Example Response**:
```json
{
  "id": "a1111111-1111-1111-1111-111111111111",
  "status": "approved",
  "approved_by": "supervisor.sarah",
  "approved_at": "2026-09-14T19:55:00Z",
  "title": "Reroute TRK-1002 via RT-CAPE",
  "reason": "Shipment TRK-1002 is rerouted via RT-CAPE because current route is blocked by 'Red Sea Threat'.",
  "requires_approval": true,
  "updated_at": "2026-09-14T19:55:00Z"
}
```

---

## 3. Governance, Invariants & Security Boundaries

1. **Direct Database Isolation**: MCP tools **NEVER** connect directly to PostgreSQL or execute SQL queries. All operations must pass through the FastAPI REST layer.
2. **Pure Python Engine Boundary**: All 11 engines remain 100% pure Python without FastAPI, SQLAlchemy, or MCP protocol imports.
3. **Approval State Machine Invariants**:
   - `pending` ➔ `approved`, `rejected`, or `deferred`
   - `approved` ➔ `implemented`
   - Terminal states cannot be reverted without creating a new recommendation.
4. **Audit Immutability**: All state-changing operations create append-only records in `audit_logs` capturing `actor`, `actor_type`, `action`, `previous_state`, `new_state`, and `reasoning`.
