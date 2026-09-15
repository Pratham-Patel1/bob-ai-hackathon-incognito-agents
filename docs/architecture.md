# SupplyChainOS — Architecture Document

> **Version**: 2.0.0 | **Last Updated**: 2026-09-14
> **Status**: Living document — updated as implementation progresses.

---

## 1. Problem Statement

Supply-chain disruptions — weather events, port strikes, geopolitical crises —
cascade across hundreds of active shipments in ways that are impossible to
track manually. Fleet assets (trucks, containers, vessels) sit idle while
other routes are overloaded. Cold-chain shipments (vaccines, perishables) are
especially vulnerable — a single temperature excursion across any leg can
spoil a $500K+ cargo, but breaches are only discovered at delivery when it
is too late.

**Users**: Supply-chain operations managers, logistics coordinators, fleet
dispatchers, cold-chain quality assurance teams, and executive decision-makers.

---

## 2. Solution Overview

SupplyChainOS is an AI-powered supply-chain resilience and Digital Twin
control tower that:

1. **Detects** shipments affected by disruptions (geographic + route matching)
2. **Scores** shipment risk using deterministic factors + ML prediction
3. **Predicts** delay probability using a pre-trained RandomForest model
4. **Monitors** cold-chain temperature excursions in real time
5. **Identifies** idle and overloaded fleet assets
6. **Optimizes** alternative routes around disruption zones
7. **Recommends** alternative carriers with cost/reliability scoring
8. **Analyses** cascading disruption impact (fleet + carrier graphs)
9. **Simulates** what-if scenarios via an in-memory Digital Twin
10. **Estimates** financial exposure (SLA penalties, holding costs, cargo value)
11. **Generates** prioritized, explainable recommendations
12. **Requires** human approval for high-value or critical operations
13. **Maintains** a full immutable audit trail of all AI decisions

---

## 3. System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER / OPERATOR                           │
│                    (Browser / API Client)                         │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTPS / REST
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                   FRONTEND (Next.js 14)                          │
│          App Router │ Leaflet Maps │ Recharts                    │
│                     [PLANNED]                                    │
└────────────────────────┬─────────────────────────────────────────┘
                         │ REST API (/api/v1/*)
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI)                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │
│  │   Routers    │ │   Schemas    │ │    Config / Middleware    │  │
│  │ (endpoints)  │ │  (Pydantic)  │ │  (CORS, error handlers)  │  │
│  └──────┬───────┘ └──────────────┘ └──────────────────────────┘  │
│         │ plain dicts                                             │
│         ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              PURE PYTHON ENGINES                              │ │
│  │  DisruptionImpact │ ShipmentRisk │ PredictiveRisk            │ │
│  │  ColdChain │ FleetIntelligence │ RouteOptimizer              │ │
│  │  CarrierRecommender │ CascadeImpact │ BusinessImpact         │ │
│  │  RecommendationEngine │ DigitalTwin                          │ │
│  └──────────────────────────────────────────────────────────────┘ │
│         │ dataclass results                                       │
│         ▼                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  ORM Models  │  │ Audit Writer │  │  Seed Data Generator    │ │
│  │ (SQLAlchemy) │  │              │  │                         │ │
│  └──────┬───────┘  └──────┬───────┘  └─────────────────────────┘ │
└─────────┼─────────────────┼──────────────────────────────────────┘
          │ async queries    │ audit inserts
          ▼                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                   PostgreSQL 16                                   │
│  shipments │ disruptions │ fleet │ carriers │ routes │ temp_logs  │
│  shipment_disruptions │ recommendations │ decision_audit          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Layered Architecture

```
Layer 0:  Infrastructure    Docker, PostgreSQL, Docker Compose
Layer 1:  Data Access       async SQLAlchemy models, database.py, seed.py
Layer 2:  API               FastAPI routers, Pydantic schemas, CORS, auth headers
Layer 3:  Business Logic    Pure Python engines (NO framework imports)
Layer 4:  ML / AI           scikit-learn model artifact, feature extraction
Layer 5:  Presentation      Next.js 14 frontend (PLANNED)
Layer 6:  Integration       MCP server, Bob Copilot (PLANNED)
```

**Key invariant**: Layers 3 and 4 have ZERO dependencies on Layers 0–2.
Routers (Layer 2) act as the adapter between the database (Layer 1) and
the engines (Layer 3).

---

## 5. Data Flow

### 5.1 Disruption Detection → Recommendation Flow

```
New Disruption Created (POST /api/v1/disruptions)
    │
    ├─→ DisruptionImpactEngine.run()
    │       Input:  disruption dict, active shipment dicts
    │       Output: ImpactResult (affected shipments, scores, factors)
    │
    ├─→ Persist ShipmentDisruption M2M records
    │
    ├─→ Write audit record (disruption_created)
    │
    └─→ Return disruption with impact count
```

### 5.2 Full Recommendation Pipeline

```
POST /api/v1/recommendations/generate?disruption_id=...
    │
    ├─→ Load all operational data from DB (shipments, routes, carriers, fleet, temp logs)
    │
    ├─→ RecommendationEngine.run()  ← ORCHESTRATOR
    │       │
    │       ├─→ DisruptionImpactEngine.run()
    │       │       → affected shipment IDs
    │       │
    │       ├─→ ShipmentRiskEngine.run()  (per affected shipment)
    │       │       → deterministic risk score + factors
    │       │
    │       ├─→ PredictiveRiskEngine.run()  (per affected shipment)
    │       │       → ML delay probability
    │       │
    │       ├─→ Combined score = 0.6 × deterministic + 0.4 × ML
    │       │
    │       ├─→ RouteOptimizationEngine.run()  (per shipment, if risk ≥ 0.3)
    │       │       → ranked alternative routes
    │       │
    │       ├─→ CarrierRecommendationEngine.run()  (per shipment, if risk ≥ 0.5)
    │       │       → ranked alternative carriers
    │       │
    │       ├─→ FleetIntelligenceEngine.suggest_redeployments()
    │       │       → idle vehicle → needy shipment matches
    │       │
    │       ├─→ CascadingImpactEngine.run()
    │       │       → secondary affected shipments (fleet + carrier cascade)
    │       │
    │       └─→ BusinessImpactEngine.run()
    │               → financial exposure (delay cost, SLA penalties)
    │
    ├─→ Persist Recommendation records (status: pending)
    │
    ├─→ Write audit records (rec_generated)
    │
    └─→ Return recommendation IDs + affected count
```

### 5.3 Shipment Risk Calculation

```
GET /api/v1/shipments/{id}/risk
    │
    ├─→ Load shipment, active disruptions (M2M), carrier, temp logs
    │
    ├─→ ShipmentRiskEngine.run()
    │       Factors: disruption severity, compound disruptions,
    │                urgency (<24h), cargo value, cold-chain, carrier reliability
    │
    ├─→ PredictiveRiskEngine.run()
    │       ML artifact: RandomForest (joblib)
    │
    ├─→ Combined score, persist to shipment record
    │
    ├─→ Write audit record (risk_calculated)
    │
    └─→ Return deterministic + ML + combined scores with explanations
```

---

## 6. AI Decision Loop

The AI decision loop is the core intelligence cycle:

```
 ┌──────────────────────────────────────────────┐
 │  1. DETECT                                    │
 │     DisruptionImpactEngine                    │
 │     ColdChainAnomalyEngine                   │
 │     FleetIntelligenceEngine (idle detection)  │
 └──────────────┬───────────────────────────────┘
                │
 ┌──────────────▼───────────────────────────────┐
 │  2. ASSESS                                    │
 │     ShipmentRiskEngine (deterministic)        │
 │     PredictiveRiskEngine (ML)                 │
 │     CascadingImpactEngine (secondary effects) │
 │     BusinessImpactEngine (financial)          │
 └──────────────┬───────────────────────────────┘
                │
 ┌──────────────▼───────────────────────────────┐
 │  3. OPTIMIZE                                  │
 │     RouteOptimizationEngine                   │
 │     CarrierRecommendationEngine               │
 │     FleetIntelligenceEngine (redeployment)    │
 └──────────────┬───────────────────────────────┘
                │
 ┌──────────────▼───────────────────────────────┐
 │  4. RECOMMEND                                 │
 │     RecommendationEngine (orchestrator)       │
 │     Priority: critical > high > medium > low  │
 └──────────────┬───────────────────────────────┘
                │
 ┌──────────────▼───────────────────────────────┐
 │  5. APPROVE                                   │
 │     Human-in-the-loop approval                │
 │     State: pending → approved → implemented   │
 │     or: pending → rejected / deferred         │
 └──────────────┬───────────────────────────────┘
                │
 ┌──────────────▼───────────────────────────────┐
 │  6. AUDIT                                     │
 │     Every decision recorded with:             │
 │     actor, reasoning, previous/new state      │
 └───────────────────────────────────────────────┘
```

---

## 7. Business AI Loop

```
Disruption Event
    ↓
Impact Detection (which shipments are affected?)
    ↓
Risk Assessment (how severe is the risk?)
    ↓
Prediction (what is the delay probability?)
    ↓
Cascade Analysis (what secondary shipments are affected?)
    ↓
Business Impact (what is the financial exposure?)
    ↓
Optimization (what alternative routes/carriers exist?)
    ↓
Recommendation Generation (what should we do?)
    ↓
Human Approval (is the action authorized?)
    ↓
Implementation (execute the approved action)
    ↓
Audit Trail (record the full decision chain)
```

---

## 8. Engineering AI/SDLC Loop

```
Code Change
    ↓
Unit Tests (pytest — engines + seed data)
    ↓
CI Validation (.github/workflows/validate.yml)
    ↓
Docker Build (docker compose up --build)
    ↓
Integration Test (API endpoints + DB)
    ↓
Review (AGENTS.md governs AI agent behavior)
    ↓
Documentation Update (architecture, contracts, ownership)
```

All AI decisions are:
- **Explainable**: Every risk score and recommendation includes `explanation`,
  `factors`, and `reasoning_factors` fields.
- **Auditable**: Every state change writes to `decision_audit`.
- **Reversible**: Recommendations can be rejected or deferred.

---

## 9. Module Responsibilities

### 9.1 Engines (Pure Python — `src/backend/engines/`)

| Engine                      | File                      | Purpose                                     | Status        |
|-----------------------------|---------------------------|---------------------------------------------|---------------|
| DisruptionImpactEngine      | `disruption_impact.py`    | Identify shipments affected by disruption   | IMPLEMENTED   |
| ShipmentRiskEngine          | `shipment_risk.py`        | Deterministic weighted-sum risk scoring     | IMPLEMENTED   |
| PredictiveRiskEngine        | `predictive_risk.py`      | ML-based delay probability                  | IMPLEMENTED   |
| ColdChainAnomalyEngine      | `cold_chain.py`           | Temperature excursion detection             | IMPLEMENTED   |
| FleetIntelligenceEngine      | `fleet_intelligence.py`   | Idle/overloaded + redeployment suggestions  | IMPLEMENTED   |
| RouteOptimizationEngine      | `route_optimizer.py`      | Rank alternative routes                     | IMPLEMENTED   |
| CarrierRecommendationEngine  | `carrier_recommender.py`  | Rank alternative carriers                   | IMPLEMENTED   |
| CascadingImpactEngine        | `cascade_impact.py`       | First-order fleet + carrier cascade         | IMPLEMENTED   |
| BusinessImpactEngine         | `business_impact.py`      | Financial exposure calculation              | IMPLEMENTED   |
| RecommendationEngine         | `recommendation_engine.py`| Orchestrator — calls all engines            | IMPLEMENTED   |
| DigitalTwinEngine            | `digital_twin.py`         | In-memory what-if simulation                | IMPLEMENTED   |

### 9.2 Routers (FastAPI — `src/backend/routers/`)

| Router              | File                 | Prefix                | Status        |
|---------------------|----------------------|-----------------------|---------------|
| Health              | `health.py`          | `/health`             | IMPLEMENTED   |
| Shipments           | `shipments.py`       | `/shipments`          | IMPLEMENTED   |
| Disruptions         | `disruptions.py`     | `/disruptions`        | IMPLEMENTED   |
| Fleet               | `fleet.py`           | `/fleet`              | IMPLEMENTED   |
| Recommendations     | `recommendations.py` | `/recommendations`    | IMPLEMENTED   |
| Simulation          | `simulation.py`      | `/simulation`         | IMPLEMENTED   |
| Audit               | `audit.py`           | `/audit`              | IMPLEMENTED   |
| Carriers            | `reference.py`       | `/carriers`           | IMPLEMENTED   |
| Routes              | `reference.py`       | `/routes`             | IMPLEMENTED   |

### 9.3 Database Models (SQLAlchemy — `src/backend/models/`)

| Model              | Table                     | Status      |
|--------------------|---------------------------|-------------|
| Shipment           | `shipments`               | IMPLEMENTED |
| Disruption         | `disruptions`             | IMPLEMENTED |
| ShipmentDisruption | `shipment_disruptions`    | IMPLEMENTED |
| Fleet              | `fleet`                   | IMPLEMENTED |
| Carrier            | `carriers`                | IMPLEMENTED |
| Route              | `routes`                  | IMPLEMENTED |
| TemperatureLog     | `temperature_logs`        | IMPLEMENTED |
| Recommendation     | `recommendations`         | IMPLEMENTED |
| DecisionAudit      | `decision_audit`          | IMPLEMENTED |

---

## 10. Backend Architecture

### 10.1 Request Flow

```
HTTP Request
    ↓
FastAPI Middleware (CORS, error handlers)
    ↓
Router Endpoint (async def)
    ↓
Pydantic Validation (request body / query params)
    ↓
Database Query (async SQLAlchemy → dict conversion)
    ↓
Engine Call (pure Python — dataclass result)
    ↓
Database Persist (update models, write audit)
    ↓
Pydantic Response Serialization
    ↓
HTTP Response (JSON)
```

### 10.2 Configuration

All configuration via environment variables (`src/.env`):
- `DATABASE_URL` — PostgreSQL connection string
- `APP_ENV` — `development` | `demo` | `production`
- `APPROVAL_THRESHOLD_USD` — cargo value threshold for human approval (default: 50000)
- `ML_DETERMINISTIC_WEIGHT` — weight for deterministic risk (default: 0.6)
- `ML_PREDICTIVE_WEIGHT` — weight for ML risk (default: 0.4)

---

## 11. Engine Architecture

### 11.1 Engine Contract Pattern

Every engine follows this pattern:

```python
"""
<EngineName> — <one-line purpose>.

Pure Python — no FastAPI or SQLAlchemy imports.
"""
from dataclasses import dataclass, field
from typing import Any

@dataclass
class EngineOutput:
    # typed output fields
    explanation: str = ""

def run(
    input_data: dict[str, Any],
    # additional inputs as needed
) -> EngineOutput:
    """
    Pure function: dict in → dataclass out.
    No side effects.
    """
    ...
```

### 11.2 Engine Dependency Graph

```
RecommendationEngine (orchestrator)
    ├─→ DisruptionImpactEngine
    ├─→ ShipmentRiskEngine
    ├─→ PredictiveRiskEngine
    ├─→ RouteOptimizationEngine
    ├─→ CarrierRecommendationEngine
    ├─→ FleetIntelligenceEngine
    ├─→ CascadingImpactEngine
    └─→ BusinessImpactEngine

DigitalTwinEngine (simulation)
    ├─→ RecommendationEngine (full pipeline)
    ├─→ ShipmentRiskEngine
    └─→ PredictiveRiskEngine
```

---

## 12. Database Responsibility Boundary

```
┌───────────────────────────────────┐
│         ROUTERS (Layer 2)         │
│  ┌─────────────────────────────┐  │
│  │  1. Query DB → get models   │  │
│  │  2. Convert to dicts        │  │
│  │  3. Call engine(dicts)      │  │
│  │  4. Persist results         │  │
│  │  5. Write audit             │  │
│  │  6. Return JSON response    │  │
│  └─────────────────────────────┘  │
│                                   │
│  CAN import: FastAPI, SQLAlchemy  │
│  CAN access: database session    │
└───────────────────────────────────┘

┌───────────────────────────────────┐
│        ENGINES (Layer 3)          │
│  ┌─────────────────────────────┐  │
│  │  1. Receive plain dicts     │  │
│  │  2. Apply business logic    │  │
│  │  3. Return dataclass        │  │
│  └─────────────────────────────┘  │
│                                   │
│  CANNOT import: FastAPI, SQLAlchemy│
│  CANNOT access: database session  │
│  CANNOT write: files, network     │
└───────────────────────────────────┘
```

---

## 13. Frontend Responsibility Boundary

**Status**: PLANNED (not yet implemented)

The frontend will:
- Be a Next.js 14 App Router application
- Consume the REST API at `/api/v1/*`
- Use Leaflet for geographic visualization (shipment positions, disruption zones)
- Use Recharts for risk scores, fleet utilization, business impact
- Provide a recommendation approval UI (approve/reject/defer)
- Provide a Digital Twin simulation UI
- NOT contain any business logic — all logic lives in the engines

---

## 14. MCP / Bob Copilot Future Integration

**Status**: PLANNED (Phase 2 — not yet implemented)

### 14.1 Planned Architecture

```
User
 ↓
Bob Copilot (natural language)
 ↓
MCP Protocol
 ↓
MCP Server (tool definitions)
 ↓
Backend API (/api/v1/*)
 ↓
Engine (pure Python)
 ↓
Result (dataclass → JSON)
 ↓
MCP Response
 ↓
Bob Copilot (explanation to user)
```

### 14.2 Planned MCP Tools

| Tool Name                 | Maps To API                                 |
|---------------------------|---------------------------------------------|
| `analyze_disruption`      | `GET /api/v1/disruptions/{id}/impact`       |
| `get_shipment_risk`       | `GET /api/v1/shipments/{id}/risk`           |
| `check_cold_chain`        | `GET /api/v1/shipments/{id}/temperature`    |
| `get_fleet_status`        | `GET /api/v1/fleet/redeployment-suggestions`|
| `find_alternative_routes` | via recommendation engine                   |
| `simulate_scenario`       | `POST /api/v1/simulation/run`               |
| `get_recommendations`     | `GET /api/v1/recommendations`               |
| `approve_recommendation`  | `POST /api/v1/recommendations/{id}/approve` |
| `get_cascade_impact`      | `GET /api/v1/disruptions/{id}/cascade`      |

### 14.3 MCP Design Principles

- MCP tools are thin wrappers around existing API endpoints.
- MCP does NOT bypass the approval state machine.
- All MCP actions are audited just like direct API calls.
- Bob Copilot receives engine `explanation` fields for human-readable responses.

---

## 15. Human-in-the-Loop Architecture

### 15.1 Approval State Machine

```
                 ┌──────────┐
    generate ──→ │ pending  │
                 └────┬─────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    ┌─────────┐ ┌──────────┐ ┌──────────┐
    │approved │ │ rejected │ │ deferred │
    └────┬────┘ └──────────┘ └────┬─────┘
         │                        │
         ▼                        │ (can reject later)
    ┌───────────┐                 │
    │implemented│                 ▼
    └───────────┘           ┌──────────┐
                            │ rejected │
                            └──────────┘
```

### 15.2 Approval Triggers

A recommendation `requires_approval = True` when:
- Cargo value exceeds `APPROVAL_THRESHOLD_USD` (default: $50,000)
- Disruption severity is `critical`
- Recommendation type is `fleet_redeploy`
- Carrier cost index exceeds 120% of current carrier

---

## 16. Audit Architecture

Every state-changing operation writes to the `decision_audit` table:

| Field            | Description                                |
|------------------|--------------------------------------------|
| `id`             | UUID primary key                           |
| `entity_type`    | `shipment`, `disruption`, `recommendation`, `simulation` |
| `entity_id`      | UUID of the affected entity                |
| `action`         | `disruption_created`, `risk_calculated`, `rec_generated`, `rec_approved`, etc. |
| `actor`          | Who triggered the action (name or `system`)|
| `actor_type`     | `human` or `system`                        |
| `reasoning`      | Why the decision was made (from engine `explanation`) |
| `previous_state` | JSON snapshot of state before change       |
| `new_state`      | JSON snapshot of state after change        |
| `extra_metadata` | Additional context (ML scores, disruption count, etc.) |
| `created_at`     | UTC timestamp                              |

---

## 17. Digital Twin Architecture

The Digital Twin provides in-memory what-if simulation:

```
Scenario Input (hypothetical disruption parameters)
    ↓
Build hypothetical disruption dict (NOT persisted to DB)
    ↓
Run full RecommendationEngine pipeline in memory
    ↓
Collect: impact, risk scores, cascade, business impact, recommendations
    ↓
Write exactly ONE audit record (simulation_run) for traceability
    ↓
Return complete SimulationResult (no shipment state modified)
```

**Key property**: The Digital Twin uses the SAME engines as the live pipeline.
The only difference is that the hypothetical disruption is constructed in memory
and no shipment state is persisted.

---

## 18. Security Boundary

```
┌──────────────────────────────────────────┐
│              PUBLIC ZONE                  │
│  Frontend (PLANNED), API docs (/docs)    │
└──────────────────┬───────────────────────┘
                   │ CORS (configurable)
┌──────────────────▼───────────────────────┐
│           APPLICATION ZONE               │
│  FastAPI backend (port 8000)             │
│  X-Operator-Name header for actor ID     │
└──────────────────┬───────────────────────┘
                   │ asyncpg (internal Docker network)
┌──────────────────▼───────────────────────┐
│            DATABASE ZONE                  │
│  PostgreSQL (port 5432, internal only)   │
└──────────────────────────────────────────┘
```

- All secrets in `.env` (never committed).
- No authentication implemented in MVP (header-based actor identification).
- Database credentials via environment variables.
- CORS restricted to `CORS_ORIGINS` env var.

---

## 19. Deployment Architecture

```
docker compose up --build

┌─────────────────────────────────────────────┐
│  Docker Compose Network                      │
│                                              │
│  ┌───────────────┐   ┌───────────────────┐  │
│  │  PostgreSQL   │   │    Backend         │  │
│  │  (db)         │←──│  (FastAPI/Uvicorn) │  │
│  │  Port: 5432   │   │  Port: 8000       │  │
│  │  Health check │   │  --reload          │  │
│  └───────────────┘   └───────────────────┘  │
│                                              │
│  ┌───────────────────────────────────────┐   │
│  │  Frontend (PLANNED — commented out)   │   │
│  │  Port: 3000                           │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

- Backend depends on `db` service health check.
- Source code mounted as volume for live reload during development.
- ML artifact (`risk_model.joblib`) included in the Docker image.

---

## 20. Current Implementation Status

### IMPLEMENTED ✅

| Component                  | Status       | Notes                                          |
|----------------------------|--------------|-------------------------------------------------|
| PostgreSQL schema (9 models)| ✅ Complete  | All tables defined and auto-created at startup  |
| Seed data                  | ✅ Complete  | Synthetic shipments, disruptions, fleet, carriers, routes, temp logs |
| All 11 engines             | ✅ Complete  | Pure Python, fully testable, with explanations  |
| Full API (8 routers)       | ✅ Complete  | Health, shipments, disruptions, fleet, recommendations, simulation, audit, reference |
| Approval state machine     | ✅ Complete  | pending → approved/rejected/deferred → implemented |
| Audit trail                | ✅ Complete  | All decisions logged with actor, reasoning, state |
| ML training pipeline       | ✅ Complete  | Feature extraction, synthetic data, RandomForest |
| Docker Compose             | ✅ Complete  | Backend + PostgreSQL with health checks         |
| Engine unit tests          | ✅ Complete  | 7 test files covering core engines              |

### PLANNED 📋

| Component                  | Status       | Notes                                          |
|----------------------------|--------------|-------------------------------------------------|
| Next.js 14 frontend        | 📋 Planned  | Dockerfile exists, service commented out        |
| MCP server                 | 📋 Planned  | Architecture designed, not implemented          |
| Bob Copilot integration    | 📋 Planned  | Depends on MCP server                           |
| watsonx.ai integration     | 📋 Planned  | Config vars exist, no implementation yet        |
| Slack notifications        | 📋 Planned  | Config var exists, no implementation yet        |

### FUTURE 🔮

| Component                  | Notes                                          |
|----------------------------|-------------------------------------------------|
| Authentication / RBAC      | Production auth beyond header-based actor ID   |
| Multi-hop cascade (depth>1)| Currently first-order only                     |
| Real-time data ingestion   | Currently batch/on-demand only                 |
| Horizontal scaling         | Stateless backend supports it architecturally  |
