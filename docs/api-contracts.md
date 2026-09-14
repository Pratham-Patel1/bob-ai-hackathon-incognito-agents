# SupplyChainOS — API Contracts

> **Version**: 1.0.0 | **Last Updated**: 2026-09-14
> Documents the current and planned API surface for SupplyChainOS.
> Base URL: `/api/v1`

---

## Status Legend

| Label          | Meaning                                    |
|----------------|--------------------------------------------|
| ✅ IMPLEMENTED | Endpoint exists and is functional          |
| 📋 PLANNED     | Endpoint is designed but not yet created   |

---

## API Summary Table

| Method | Endpoint                                     | Status         | Owner    | Engine Involved              |
|--------|----------------------------------------------|----------------|----------|------------------------------|
| GET    | `/api/v1/health`                             | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/health/db`                          | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/shipments`                          | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/shipments/{id}`                     | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/shipments/{id}/risk`                | ✅ IMPLEMENTED | Member 2 | ShipmentRisk + PredictiveRisk|
| GET    | `/api/v1/shipments/{id}/disruptions`         | ✅ IMPLEMENTED | Member 2 | None (M2M query)             |
| GET    | `/api/v1/shipments/{id}/temperature`         | ✅ IMPLEMENTED | Member 2 | ColdChainAnomaly             |
| POST   | `/api/v1/shipments/bulk-risk-refresh`        | ✅ IMPLEMENTED | Member 2 | ShipmentRisk + PredictiveRisk|
| GET    | `/api/v1/disruptions`                        | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/disruptions/{id}`                   | ✅ IMPLEMENTED | Member 2 | None                         |
| POST   | `/api/v1/disruptions`                        | ✅ IMPLEMENTED | Member 2 | DisruptionImpact             |
| PATCH  | `/api/v1/disruptions/{id}/resolve`           | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/disruptions/{id}/impact`            | ✅ IMPLEMENTED | Member 2 | DisruptionImpact             |
| GET    | `/api/v1/disruptions/{id}/affected-shipments`| ✅ IMPLEMENTED | Member 2 | None (M2M query)             |
| GET    | `/api/v1/disruptions/{id}/cascade`           | ✅ IMPLEMENTED | Member 2 | CascadingImpact              |
| GET    | `/api/v1/fleet`                              | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/fleet/idle`                         | ✅ IMPLEMENTED | Member 2 | None (DB query)              |
| GET    | `/api/v1/fleet/overloaded`                   | ✅ IMPLEMENTED | Member 2 | None (DB query)              |
| GET    | `/api/v1/fleet/redeployment-suggestions`     | ✅ IMPLEMENTED | Member 2 | FleetIntelligence            |
| GET    | `/api/v1/fleet/{id}`                         | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/recommendations`                    | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/recommendations/{id}`               | ✅ IMPLEMENTED | Member 2 | None                         |
| POST   | `/api/v1/recommendations/generate`           | ✅ IMPLEMENTED | Member 2 | RecommendationEngine (full)  |
| POST   | `/api/v1/recommendations/{id}/approve`       | ✅ IMPLEMENTED | Member 2 | None (state machine)         |
| POST   | `/api/v1/recommendations/{id}/reject`        | ✅ IMPLEMENTED | Member 2 | None (state machine)         |
| POST   | `/api/v1/recommendations/{id}/defer`         | ✅ IMPLEMENTED | Member 2 | None (state machine)         |
| POST   | `/api/v1/recommendations/{id}/implement`     | ✅ IMPLEMENTED | Member 2 | None (state machine)         |
| POST   | `/api/v1/simulation/run`                     | ✅ IMPLEMENTED | Member 2 | DigitalTwin (full pipeline)  |
| GET    | `/api/v1/audit`                              | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/audit/{entity_type}/{entity_id}`    | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/carriers`                           | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/carriers/{id}`                      | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/routes`                             | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/routes/{id}`                        | ✅ IMPLEMENTED | Member 2 | None                         |
| GET    | `/api/v1/routes/{id}/alternatives`           | ✅ IMPLEMENTED | Member 2 | None (DB query)              |

---

## CURRENTLY IMPLEMENTED ENDPOINTS

---

### Health

#### `GET /api/v1/health` ✅

**Purpose**: Liveness check — confirms the application is running.
**Owner**: Member 2
**Engine**: None

**Parameters**: None

**Response** (200):
```json
{
  "status": "ok",
  "service": "SupplyChainOS"
}
```

---

#### `GET /api/v1/health/db` ✅

**Purpose**: Database connectivity check — confirms PostgreSQL is reachable.
**Owner**: Member 2
**Engine**: None

**Parameters**: None

**Response** (200):
```json
{
  "status": "ok",
  "database": "connected"
}
```

**Error** (503):
```json
{
  "detail": "Database unavailable: <error>"
}
```

---

### Shipments

#### `GET /api/v1/shipments` ✅

**Purpose**: List all shipments with optional filters.
**Owner**: Member 2
**Engine**: None

**Query Parameters**:
| Parameter   | Type   | Required | Description                          |
|-------------|--------|----------|--------------------------------------|
| `status`    | `str`  | No       | Filter by status                     |
| `risk_level`| `str`  | No       | Filter by risk level                 |
| `carrier_id`| `str`  | No       | Filter by carrier UUID               |

**Response** (200): `list[ShipmentRead]`
```json
[
  {
    "id": "uuid",
    "tracking_number": "SHIP-001",
    "origin": "Shanghai",
    "destination": "Rotterdam",
    "origin_lat": 31.23,
    "origin_lng": 121.47,
    "destination_lat": 51.92,
    "destination_lng": 4.48,
    "current_location": "South China Sea",
    "current_lat": 20.5,
    "current_lng": 115.2,
    "carrier_id": "uuid",
    "route_id": "uuid",
    "fleet_id": "uuid|null",
    "status": "in_transit",
    "scheduled_departure": "2026-09-10T08:00:00Z",
    "scheduled_arrival": "2026-09-20T16:00:00Z",
    "estimated_arrival": null,
    "cargo_type": "general",
    "cargo_value_usd": 250000.0,
    "weight_kg": 15000.0,
    "temperature_required": false,
    "temp_min_c": null,
    "temp_max_c": null,
    "actual_arrival": null,
    "risk_score": 0.0,
    "risk_level": "low",
    "ml_risk_score": null,
    "combined_risk_score": null,
    "created_at": "2026-09-10T00:00:00Z",
    "updated_at": "2026-09-10T00:00:00Z"
  }
]
```

---

#### `GET /api/v1/shipments/{shipment_id}` ✅

**Purpose**: Get a single shipment by ID.
**Owner**: Member 2
**Engine**: None

**Path Parameters**:
| Parameter     | Type   | Required | Description    |
|---------------|--------|----------|----------------|
| `shipment_id` | `str`  | ✅       | UUID of shipment |

**Response** (200): `ShipmentRead` (same shape as list item)

**Error** (404):
```json
{ "detail": "Shipment not found" }
```

---

#### `GET /api/v1/shipments/{shipment_id}/risk` ✅

**Purpose**: Recalculate deterministic + ML risk scores for a shipment.
**Owner**: Member 2
**Engine**: `ShipmentRiskEngine` + `PredictiveRiskEngine`

**Path Parameters**: `shipment_id` (UUID)

**Response** (200):
```json
{
  "shipment_id": "uuid",
  "deterministic_score": 0.65,
  "ml_score": 0.72,
  "combined_score": 0.678,
  "risk_level": "high",
  "explanation": "Risk score 0.65 (high). Top factors: active disruption (+0.27), urgency (+0.18)",
  "factors": [
    { "name": "active_disruption", "value": 0.9, "contribution": 0.27 },
    { "name": "urgency", "value": 0.85, "contribution": 0.17 }
  ],
  "ml_top_features": [
    { "feature": "disruption_severity", "value": 3.0, "importance": 0.25 }
  ],
  "model_version": "1.0"
}
```

**Side Effects**: Updates `shipment.risk_score`, `risk_level`, `ml_risk_score`, `combined_risk_score` in DB. Writes audit record.

---

#### `GET /api/v1/shipments/{shipment_id}/disruptions` ✅

**Purpose**: List all active disruptions affecting this shipment (via M2M table).
**Owner**: Member 2
**Engine**: None

**Response** (200): `list[DisruptionRead]`

---

#### `GET /api/v1/shipments/{shipment_id}/temperature` ✅

**Purpose**: Temperature log history + cold-chain analysis.
**Owner**: Member 2
**Engine**: `ColdChainAnomalyEngine`

**Response** (200):
```json
{
  "shipment_id": "uuid",
  "temperature_required": true,
  "temp_min_c": 2.0,
  "temp_max_c": 8.0,
  "log_count": 48,
  "logs": [
    {
      "recorded_at": "2026-09-10T08:00:00Z",
      "temperature_c": 4.5,
      "is_excursion": false,
      "excursion_severity": null
    }
  ],
  "cold_chain_analysis": {
    "has_excursion": true,
    "severity": "major",
    "excursion_count": 2,
    "max_deviation_c": 3.5,
    "total_excursion_minutes": 45.0,
    "recommended_action": "Notify receiving team. Inspect cargo on arrival.",
    "explanation": "2 excursion window(s) detected. Worst severity: major."
  }
}
```

---

#### `POST /api/v1/shipments/bulk-risk-refresh` ✅

**Purpose**: Recalculate risk scores for all active shipments.
**Owner**: Member 2
**Engine**: `ShipmentRiskEngine` + `PredictiveRiskEngine`

**Request Body**: None

**Response** (200):
```json
{
  "updated_count": 15,
  "status": "ok"
}
```

**Side Effects**: Updates risk scores for all in_transit/at_risk/delayed shipments.

---

### Disruptions

#### `GET /api/v1/disruptions` ✅

**Purpose**: List disruptions with optional filters.
**Owner**: Member 2
**Engine**: None

**Query Parameters**:
| Parameter  | Type  | Required | Description                          |
|------------|-------|----------|--------------------------------------|
| `status`   | `str` | No       | Filter by status (default: non-resolved) |
| `type`     | `str` | No       | Filter by disruption type            |
| `severity` | `str` | No       | Filter by severity                   |

**Response** (200): `list[DisruptionRead]`
```json
[
  {
    "id": "uuid",
    "type": "weather",
    "severity": "high",
    "title": "Typhoon Megi",
    "description": "Category 3 typhoon...",
    "affected_region": "South China Sea",
    "epicenter_lat": 20.0,
    "epicenter_lng": 115.0,
    "affected_radius_km": 300.0,
    "affected_route_codes": ["SCS-001", "SCS-002"],
    "status": "active",
    "start_time": "2026-09-12T00:00:00Z",
    "estimated_end_time": "2026-09-15T00:00:00Z",
    "source": "manual",
    "actual_end_time": null,
    "created_at": "2026-09-12T00:00:00Z",
    "updated_at": "2026-09-12T00:00:00Z"
  }
]
```

---

#### `GET /api/v1/disruptions/{disruption_id}` ✅

**Purpose**: Get a single disruption.
**Owner**: Member 2

**Error** (404): `{ "detail": "Disruption not found" }`

---

#### `POST /api/v1/disruptions` ✅

**Purpose**: Create a disruption and trigger impact analysis.
**Owner**: Member 2
**Engine**: `DisruptionImpactEngine`

**Request Headers**:
| Header           | Type   | Default  | Description              |
|------------------|--------|----------|--------------------------|
| `X-Operator-Name`| `str`  | `system` | Name of operator/actor   |

**Request Body** (`DisruptionCreate`):
```json
{
  "type": "weather",
  "severity": "high",
  "title": "Typhoon Megi",
  "description": "Category 3 typhoon affecting South China Sea",
  "affected_region": "South China Sea",
  "epicenter_lat": 20.0,
  "epicenter_lng": 115.0,
  "affected_radius_km": 300.0,
  "affected_route_codes": ["SCS-001", "SCS-002"],
  "start_time": "2026-09-12T00:00:00Z",
  "estimated_end_time": "2026-09-15T00:00:00Z",
  "source": "manual"
}
```

**Response** (201): `DisruptionRead`

**Side Effects**:
- Creates disruption record.
- Runs `DisruptionImpactEngine` on all active shipments.
- Creates `shipment_disruptions` M2M records for affected shipments.
- Writes audit record (action: `disruption_created`).

---

#### `PATCH /api/v1/disruptions/{disruption_id}/resolve` ✅

**Purpose**: Mark a disruption as resolved.
**Owner**: Member 2
**Engine**: None

**Request Headers**: `X-Operator-Name`

**Response** (200): `DisruptionRead` with `status: "resolved"` and `actual_end_time` set.

**Side Effects**: Writes audit record (action: `disruption_resolved`).

---

#### `GET /api/v1/disruptions/{disruption_id}/impact` ✅

**Purpose**: Run DisruptionImpactEngine on-demand for a disruption.
**Owner**: Member 2
**Engine**: `DisruptionImpactEngine`

**Response** (200):
```json
{
  "disruption_id": "uuid",
  "affected_count": 5,
  "impacted_shipments": [
    {
      "shipment_id": "uuid",
      "impact_reason": "geo_intersection",
      "distance_to_epicenter_km": 45.23,
      "impact_score": 75,
      "impact_level": "CRITICAL",
      "estimated_delay_hours": 42.0,
      "factors": [
        "High severity disruption (+45)",
        "Shipment intersects disruption area (+10)",
        "Shipment is within 50 km of disruption (+10)"
      ]
    }
  ]
}
```

---

#### `GET /api/v1/disruptions/{disruption_id}/affected-shipments` ✅

**Purpose**: Query the shipment_disruptions join table for persisted impact records.
**Owner**: Member 2
**Engine**: None (M2M query)

**Response** (200):
```json
[
  {
    "shipment_id": "uuid",
    "disruption_id": "uuid",
    "impact_reason": "geo_intersection",
    "distance_to_epicenter_km": 45.23,
    "created_at": "2026-09-12T00:00:00Z"
  }
]
```

---

#### `GET /api/v1/disruptions/{disruption_id}/cascade` ✅

**Purpose**: Run CascadingImpactEngine for a disruption.
**Owner**: Member 2
**Engine**: `CascadingImpactEngine`

**Response** (200):
```json
{
  "disruption_id": "uuid",
  "direct_count": 5,
  "secondary_count": 3,
  "total_value_at_risk_usd": 750000.0,
  "total_delay_hours_estimate": 30.0,
  "explanation": "5 shipments directly affected. 3 secondary...",
  "cascade_chain": [
    {
      "shipment_id": "uuid",
      "tracking_number": "SHIP-008",
      "level": 1,
      "impact_type": "fleet_cascade",
      "caused_by_shipment_id": "uuid",
      "estimated_delay_hours": 12.0
    }
  ]
}
```

---

### Fleet

#### `GET /api/v1/fleet` ✅

**Purpose**: List all fleet vehicles with optional status filter.
**Owner**: Member 2
**Engine**: None

**Query Parameters**:
| Parameter | Type  | Required | Description         |
|-----------|-------|----------|---------------------|
| `status`  | `str` | No       | Filter by status    |

**Response** (200): `list[FleetRead]`

---

#### `GET /api/v1/fleet/idle` ✅

**Purpose**: List idle fleet vehicles (utilization < 20%, status = active).
**Owner**: Member 2
**Engine**: None (DB query)

**Response** (200): `list[FleetRead]`

---

#### `GET /api/v1/fleet/overloaded` ✅

**Purpose**: List overloaded fleet vehicles (utilization > 95%).
**Owner**: Member 2
**Engine**: None (DB query)

**Response** (200): `list[FleetRead]`

---

#### `GET /api/v1/fleet/redeployment-suggestions` ✅

**Purpose**: Get fleet analysis + redeployment suggestions.
**Owner**: Member 2
**Engine**: `FleetIntelligenceEngine`

**Response** (200):
```json
{
  "fleet_analysis": {
    "idle_count": 3,
    "overloaded_count": 1,
    "idle_vehicle_ids": ["uuid1", "uuid2", "uuid3"],
    "overloaded_vehicle_ids": ["uuid4"],
    "utilization_histogram": {
      "0-20": 3,
      "20-50": 5,
      "50-80": 8,
      "80-95": 3,
      "95-100": 1
    }
  },
  "redeployment_suggestions": [
    {
      "vehicle_id": "uuid1",
      "target_shipment_id": "uuid-ship",
      "distance_km": 150.5,
      "reason": "Idle vehicle TRK-007 (truck) redeployed to shipment SHIP-012..."
    }
  ]
}
```

---

#### `GET /api/v1/fleet/{fleet_id}` ✅

**Purpose**: Get a single fleet vehicle.
**Owner**: Member 2

**Error** (404): `{ "detail": "Fleet vehicle not found" }`

---

### Recommendations

#### `GET /api/v1/recommendations` ✅

**Purpose**: List recommendations with optional filters.
**Owner**: Member 2
**Engine**: None

**Query Parameters**:
| Parameter  | Type  | Required | Description              |
|------------|-------|----------|--------------------------|
| `status`   | `str` | No       | Filter by status         |
| `type`     | `str` | No       | Filter by recommendation type |
| `priority` | `str` | No       | Filter by priority       |

**Response** (200): `list[RecommendationRead]`
```json
[
  {
    "id": "uuid",
    "shipment_id": "uuid|null",
    "disruption_id": "uuid|null",
    "type": "reroute",
    "priority": "high",
    "title": "Reroute SHIP-001 via MED-003",
    "description": "Alternative route MED-003...",
    "reason": "Shipment SHIP-001 is rerouted via MED-003 because...",
    "reasoning_factors": [
      { "factor": "active_disruption", "value": 0.9, "contribution": 0.27, "weight": 0.3 }
    ],
    "alternative_route_id": "uuid|null",
    "alternative_carrier_id": "uuid|null",
    "estimated_savings_usd": 1250.0,
    "estimated_delay_reduction_hours": 12.0,
    "requires_approval": true,
    "status": "pending",
    "approved_by": null,
    "approved_at": null,
    "created_at": "2026-09-12T00:00:00Z",
    "updated_at": "2026-09-12T00:00:00Z"
  }
]
```

---

#### `GET /api/v1/recommendations/{rec_id}` ✅

**Purpose**: Get a single recommendation.
**Owner**: Member 2

**Error** (404): `{ "detail": "Recommendation not found" }`

---

#### `POST /api/v1/recommendations/generate` ✅

**Purpose**: Trigger RecommendationEngine for a given disruption.
**Owner**: Member 2
**Engine**: `RecommendationEngine` (full orchestrator pipeline)

**Query Parameters**:
| Parameter      | Type  | Required | Description          |
|----------------|-------|----------|----------------------|
| `disruption_id`| `str` | ✅       | UUID of disruption   |

**Response** (200):
```json
{
  "created_count": 8,
  "recommendation_ids": ["uuid1", "uuid2", "..."],
  "disruption_id": "uuid",
  "affected_shipment_count": 5
}
```

**Side Effects**:
- Persists all generated recommendations (status: `pending`).
- Writes audit records (action: `rec_generated`) for each recommendation.

---

#### `POST /api/v1/recommendations/{rec_id}/approve` ✅

**Purpose**: Approve a pending recommendation.
**Owner**: Member 2
**Engine**: None (state machine)

**Request Body** (`ApprovalAction`):
```json
{
  "actor": "John Smith",
  "notes": "Approved after review of alternative route."
}
```

**Response** (200): `RecommendationRead` with `status: "approved"`

**Error** (409): `{ "detail": "Cannot approve: status is '<current>'" }`

**State Constraint**: Only from `pending`.

**Side Effects**: Updates `approved_by`, `approved_at`. Writes audit record.

---

#### `POST /api/v1/recommendations/{rec_id}/reject` ✅

**Purpose**: Reject a pending or deferred recommendation.
**Owner**: Member 2

**Request Body**: `ApprovalAction`

**State Constraint**: Only from `pending` or `deferred`.

**Side Effects**: Writes audit record (action: `rec_rejected`).

---

#### `POST /api/v1/recommendations/{rec_id}/defer` ✅

**Purpose**: Defer a pending recommendation for later review.
**Owner**: Member 2

**Request Body**: `ApprovalAction`

**State Constraint**: Only from `pending`.

**Side Effects**: Writes audit record (action: `rec_deferred`).

---

#### `POST /api/v1/recommendations/{rec_id}/implement` ✅

**Purpose**: Mark a recommendation as implemented.
**Owner**: Member 2

**Request Body**: `ApprovalAction`

**State Constraint**:
- If `requires_approval = true`: only from `approved`.
- If `requires_approval = false`: from `pending` or `approved`.

**Error** (409): `{ "detail": "This recommendation requires approval before implementation. Current status: '<status>'" }`

**Side Effects**: Writes audit record (action: `rec_implemented`).

---

### Simulation (Digital Twin)

#### `POST /api/v1/simulation/run` ✅

**Purpose**: Run a what-if Digital Twin simulation.
**Owner**: Member 2
**Engine**: `DigitalTwinEngine` (full pipeline)

**Request Body** (`SimulationScenario`):
```json
{
  "disruption_type": "weather",
  "disruption_severity": "critical",
  "epicenter_lat": 20.0,
  "epicenter_lng": 115.0,
  "affected_radius_km": 500.0,
  "affected_route_codes": ["SCS-001"],
  "title": "What-if: Category 5 Typhoon",
  "description": "Simulate impact of a major typhoon",
  "shipment_ids": null
}
```

**Response** (200):
```json
{
  "scenario_summary": {
    "name": "What-if: Category 5 Typhoon",
    "disruption_type": "weather",
    "severity": "critical",
    "affected_radius_km": 500.0,
    "horizon_hours": 72.0,
    "total_affected_shipments": 8,
    "total_secondary_shipments": 3,
    "total_cargo_value_at_risk_usd": 2500000.0,
    "total_cost_of_delay_usd": 15000.0,
    "penalty_exposure_usd": 25000.0,
    "sla_breach_count": 5,
    "recommendation_count": 12
  },
  "affected_shipment_count": 8,
  "risk_scores": [
    { "shipment_id": "uuid", "combined_risk_score": 0.85 }
  ],
  "cascade_analysis": {
    "direct_count": 8,
    "secondary_count": 3,
    "explanation": "8 shipments directly affected..."
  },
  "business_impact": {
    "total_cargo_value_at_risk_usd": 2500000.0,
    "cost_of_delay_usd": 15000.0,
    "penalty_exposure_usd": 25000.0,
    "sla_breach_count": 5,
    "avg_delay_hours": 24.5
  },
  "top_recommendations": [
    {
      "type": "reroute",
      "priority": "critical",
      "title": "Reroute SHIP-001 via MED-003",
      "reason": "...",
      "requires_approval": true,
      "estimated_savings_usd": 1250.0
    }
  ]
}
```

**Side Effects**: Writes exactly one audit record (action: `simulation_run`). **No shipment state is modified.**

---

### Audit

#### `GET /api/v1/audit` ✅

**Purpose**: List audit trail records with optional filters.
**Owner**: Member 2
**Engine**: None

**Query Parameters**:
| Parameter     | Type  | Required | Default | Description             |
|---------------|-------|----------|---------|-------------------------|
| `entity_type` | `str` | No       | —       | Filter by entity type   |
| `actor_type`  | `str` | No       | —       | Filter by actor type    |
| `action`      | `str` | No       | —       | Filter by action        |
| `limit`       | `int` | No       | 500     | Max results             |

**Response** (200): `list[AuditRead]`
```json
[
  {
    "id": "uuid",
    "entity_type": "recommendation",
    "entity_id": "uuid",
    "action": "rec_approved",
    "actor": "John Smith",
    "actor_type": "human",
    "previous_state": { "status": "pending" },
    "new_state": { "status": "approved" },
    "reasoning": "Approved by John Smith",
    "extra_metadata": null,
    "created_at": "2026-09-12T14:30:00Z"
  }
]
```

---

#### `GET /api/v1/audit/{entity_type}/{entity_id}` ✅

**Purpose**: Get full audit history for a specific entity.
**Owner**: Member 2

**Path Parameters**:
| Parameter     | Type  | Required | Description                                    |
|---------------|-------|----------|------------------------------------------------|
| `entity_type` | `str` | ✅       | `shipment`, `disruption`, `recommendation`, `simulation` |
| `entity_id`   | `str` | ✅       | UUID of the entity                              |

**Response** (200): `list[AuditRead]` (sorted ascending by created_at)

---

### Carriers (Reference Data)

#### `GET /api/v1/carriers` ✅

**Purpose**: List active carriers.
**Owner**: Member 2

**Response** (200): `list[CarrierRead]`
```json
[
  {
    "id": "uuid",
    "name": "Maersk",
    "code": "MAERSK",
    "type": "ocean",
    "reliability_score": 0.92,
    "cost_index": 1.0,
    "coverage_regions": ["asia", "europe", "americas"],
    "active": true,
    "contact_name": "...",
    "contact_email": "...",
    "created_at": "2026-09-10T00:00:00Z"
  }
]
```

---

#### `GET /api/v1/carriers/{carrier_id}` ✅

**Purpose**: Get a single carrier.
**Error** (404): `{ "detail": "Carrier not found" }`

---

### Routes (Reference Data)

#### `GET /api/v1/routes` ✅

**Purpose**: List active routes with optional mode filter.
**Owner**: Member 2

**Query Parameters**:
| Parameter | Type  | Required | Description              |
|-----------|-------|----------|--------------------------|
| `mode`    | `str` | No       | Filter by transport mode |

**Response** (200): `list[RouteRead]`
```json
[
  {
    "id": "uuid",
    "code": "SCS-001",
    "name": "South China Sea Express",
    "origin": "Shanghai",
    "destination": "Rotterdam",
    "waypoints": null,
    "mode": "ocean",
    "distance_km": 10500.0,
    "typical_duration_hours": 504.0,
    "cost_per_kg_usd": 0.08,
    "reliability_score": 0.85,
    "active": true,
    "created_at": "2026-09-10T00:00:00Z"
  }
]
```

---

#### `GET /api/v1/routes/{route_id}` ✅

**Purpose**: Get a single route.
**Error** (404): `{ "detail": "Route not found" }`

---

#### `GET /api/v1/routes/{route_id}/alternatives` ✅

**Purpose**: Find alternative routes for the same origin/destination pair.
**Owner**: Member 2

**Response** (200): `list[RouteRead]` — routes with same origin/destination, excluding the given route.

---

### Root Endpoint

#### `GET /` ✅

**Purpose**: Service information.

**Response** (200):
```json
{
  "service": "SupplyChainOS",
  "version": "2.0.0",
  "docs": "/docs",
  "health": "/api/v1/health"
}
```

---

## PLANNED ENDPOINTS 📋

The following endpoints may be added in future phases. They are NOT
currently implemented. Do NOT create these endpoints without explicit approval.

### MCP Integration (Phase 2)

| Method | Endpoint                        | Purpose                              |
|--------|---------------------------------|--------------------------------------|
| POST   | `/mcp/tools/list`              | List available MCP tools             |
| POST   | `/mcp/tools/call`              | Execute an MCP tool                  |
| GET    | `/mcp/resources/list`          | List available MCP resources         |

### Enhanced Analytics (Phase 2+)

| Method | Endpoint                                     | Purpose                              |
|--------|----------------------------------------------|--------------------------------------|
| GET    | `/api/v1/dashboard/summary`                  | Aggregated dashboard metrics         |
| GET    | `/api/v1/shipments/{id}/risk-history`        | Historical risk score timeline       |
| GET    | `/api/v1/disruptions/{id}/business-impact`   | Direct business impact endpoint      |
| POST   | `/api/v1/simulation/compare`                 | Compare multiple scenarios           |

### Notification (Phase 2+)

| Method | Endpoint                                     | Purpose                              |
|--------|----------------------------------------------|--------------------------------------|
| POST   | `/api/v1/notifications/send`                 | Send Slack/email notification        |

---

## Error Response Format

All error responses follow this shape:

```json
{
  "detail": "Human-readable error message"
}
```

| Status Code | Meaning                                    |
|-------------|--------------------------------------------|
| 400         | Bad request / validation error             |
| 404         | Resource not found                         |
| 409         | Conflict (state machine violation)         |
| 500         | Internal server error                      |
| 503         | Service unavailable (database down)        |

---

## Common Response Headers

| Header         | Value                      |
|----------------|----------------------------|
| `Content-Type` | `application/json`         |
| CORS headers   | Based on `CORS_ORIGINS` env|

---

## Authentication

**Current state**: No authentication in MVP. The `X-Operator-Name` header
identifies the actor for audit purposes. All endpoints are publicly accessible.

**Future**: Token-based authentication or API key management will be added
for production deployment.
