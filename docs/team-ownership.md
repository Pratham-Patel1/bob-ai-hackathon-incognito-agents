# SupplyChainOS — Team Ownership Model

> **Version**: 1.0.0 | **Last Updated**: 2026-09-14
> Defines the four-member ownership model with clear boundaries.

---

## Overview

SupplyChainOS development is split across four parallel workstreams.
Each member has a clearly defined scope and should NOT modify files
owned by another member without explicit coordination.

```
 Member 1              Member 2              Member 3              Member 4
 Architecture          Backend/DB/API        AI/ML/Engines         Frontend/Demo
 MCP + Copilot         Schemas + Routers     Pure Python           Presentation
 Documentation         Docker/Infra          ML Artifacts          Visuals
 Integration           Seed Data             Training              Screenshots
 Coordination          Tests (API)           Tests (engines)       Video
      │                     │                     │                     │
      └─────────────────────┴─────────────────────┴─────────────────────┘
                          All work in parallel
```

---

## Member 1 — Architecture, Integration & Governance

### Role

Architecture lead, MCP/Copilot designer, documentation owner,
integration coordinator, AI-SDLC evidence curator, and demo/submission
coordinator.

### Responsibilities

- Project governance (`AGENTS.md`)
- Architecture documentation (`docs/architecture.md`)
- Team ownership documentation (`docs/team-ownership.md`)
- Engine integration contracts (`docs/integration-contracts.md`)
- API contracts (`docs/api-contracts.md`)
- MCP server architecture and design (Phase 2)
- Bob Copilot integration design (Phase 2)
- AI-SDLC evidence and traceability
- Integration coordination between all members
- Final validation before submission
- Demo coordination and submission metadata

### Primary Directories

```
AGENTS.md
CONTEXT.md
docs/
  ├── architecture.md
  ├── team-ownership.md
  ├── integration-contracts.md
  ├── api-contracts.md
  ├── problem-statement.md
  ├── solution-overview.md
  └── setup-guide.md
submission.yaml (shared — metadata updates)
```

### MUST NOT Modify

- `src/backend/engines/` — owned by Member 3
- `src/backend/models/` — owned by Member 2
- `src/backend/schemas/` — owned by Member 2
- `src/backend/routers/` — owned by Member 2
- `src/backend/data/seed.py` — owned by Member 2
- `src/backend/database.py` — owned by Member 2
- `src/ml/` — owned by Member 3
- `src/frontend/` — owned by Member 4 (when created)
- `.github/workflows/` — template CI, do not modify

### Dependencies on Other Members

| Depends On | For What                                              |
|------------|-------------------------------------------------------|
| Member 2   | Actual API endpoint signatures (for api-contracts.md) |
| Member 3   | Actual engine I/O shapes (for integration-contracts.md)|
| Member 4   | Demo video and screenshots (for submission)            |

### Key Principle

> **Member 1 does NOT need to wait for Members 2, 3, or 4** to begin
> architecture documentation, governance, contracts, MCP design, or
> coordination work. These are independent deliverables.

---

## Member 2 — Backend, Database & API

### Role

Backend engineer, database owner, API implementer, schema designer,
Docker/infrastructure manager.

### Responsibilities

- PostgreSQL schema and SQLAlchemy models (`src/backend/models/`)
- Pydantic request/response schemas (`src/backend/schemas/`)
- FastAPI router endpoints (`src/backend/routers/`)
- Database session management (`src/backend/database.py`)
- Application configuration (`src/backend/config.py`)
- Seed data generation (`src/backend/data/seed.py`)
- Approval/audit APIs (recommendation state machine)
- Simulation API (Digital Twin endpoint)
- Backend integration tests
- Docker/Docker Compose configuration
- `main.py` — FastAPI app factory
- `utils/audit.py` — audit writer utility

### Primary Directories

```
src/backend/
  ├── config.py
  ├── database.py
  ├── main.py
  ├── models/
  ├── schemas/
  ├── routers/
  ├── data/
  │   └── seed.py
  └── utils/
      ├── audit.py
      └── geo.py
src/docker-compose.yml
src/Dockerfile.backend
src/requirements.txt
src/.env.example
```

### MUST NOT Modify

- `src/backend/engines/` — owned by Member 3
- `src/ml/` — owned by Member 3
- `docs/architecture.md` — owned by Member 1
- `AGENTS.md` — owned by Member 1
- `src/frontend/` — owned by Member 4
- Engine business logic or algorithm internals
- ML model artifacts or training code

### Dependencies on Other Members

| Depends On | For What                                              |
|------------|-------------------------------------------------------|
| Member 3   | Engine `run()` signatures and output dataclasses      |
| Member 1   | Integration contracts and API contracts (as reference)|

### Integration Points with Member 3

The critical boundary is in the **routers**. Member 2's routers:
1. Load data from the database → convert ORM models to `dict`
2. Call `engine.run(dict_data)` → receive a `dataclass` result
3. Persist results to the database
4. Write audit records

**Member 2 writes the router glue code. Member 3 writes the engine logic.**

---

## Member 3 — AI/ML & Engine Development

### Role

AI/ML engineer, engine developer, optimization logic owner,
ML artifact trainer.

### Responsibilities

- All pure Python engines (`src/backend/engines/`)
  - `DisruptionImpactEngine` — `disruption_impact.py`
  - `ShipmentRiskEngine` — `shipment_risk.py`
  - `PredictiveRiskEngine` — `predictive_risk.py`
  - `ColdChainAnomalyEngine` — `cold_chain.py`
  - `FleetIntelligenceEngine` — `fleet_intelligence.py`
  - `RouteOptimizationEngine` — `route_optimizer.py`
  - `CarrierRecommendationEngine` — `carrier_recommender.py`
  - `CascadingImpactEngine` — `cascade_impact.py`
  - `BusinessImpactEngine` — `business_impact.py`
  - `RecommendationEngine` — `recommendation_engine.py`
  - `DigitalTwinEngine` — `digital_twin.py`
- ML training pipeline (`src/ml/`)
  - Feature extraction (`features.py`)
  - Training data generation (`generate_training_data.py`)
  - Model training (`train.py`)
  - Model evaluation (`evaluate.py`)
  - Model artifacts (`artifacts/risk_model.joblib`)
- Engine unit tests (`src/backend/tests/test_*.py`)

### Primary Directories

```
src/backend/engines/
  ├── __init__.py
  ├── disruption_impact.py
  ├── shipment_risk.py
  ├── predictive_risk.py
  ├── cold_chain.py
  ├── fleet_intelligence.py
  ├── route_optimizer.py
  ├── carrier_recommender.py
  ├── cascade_impact.py
  ├── business_impact.py
  ├── recommendation_engine.py
  └── digital_twin.py
src/ml/
  ├── features.py
  ├── train.py
  ├── evaluate.py
  ├── generate_training_data.py
  ├── artifacts/
  │   └── risk_model.joblib
  └── training_data.csv
src/backend/tests/
  ├── test_disruption_impact.py
  ├── test_shipment_risk.py
  ├── test_cold_chain.py
  ├── test_fleet_intelligence.py
  ├── test_cascade_impact.py
  ├── test_geo.py
  └── test_seed_data.py
```

### MUST NOT Modify

- `src/backend/routers/` — owned by Member 2
- `src/backend/models/` — owned by Member 2
- `src/backend/schemas/` — owned by Member 2
- `src/backend/database.py` — owned by Member 2
- `src/backend/config.py` — owned by Member 2
- `src/backend/data/seed.py` — owned by Member 2
- `docs/` — owned by Member 1
- `AGENTS.md` — owned by Member 1
- `src/frontend/` — owned by Member 4

### MUST Follow: Engine Purity Rule

All engines MUST:
- Accept plain Python `dict` objects as input
- Return Python `dataclass` objects as output
- NOT import FastAPI, SQLAlchemy, or any framework
- NOT access the database or network
- NOT have side effects (no file writes, no HTTP calls)
- Include `explanation` fields for AI explainability

### Dependencies on Other Members

| Depends On | For What                                              |
|------------|-------------------------------------------------------|
| Member 2   | Dict shapes (what keys the router will provide)       |
| Member 1   | Integration contracts (defines expected I/O)          |

---

## Member 4 — Frontend, Demo & Presentation

### Role

Frontend developer, demo producer, presentation designer,
visual/UX designer.

### Responsibilities

- Next.js 14 frontend application
- Dashboard UI (risk overview, fleet status)
- Map visualization (Leaflet — shipment positions, disruption zones)
- Chart visualization (Recharts — risk scores, fleet utilization)
- Recommendation approval UI
- Digital Twin simulation UI
- Demo video and screenshots
- Presentation slide deck
- `demo/` directory assets

### Primary Directories

```
src/frontend/           # To be created
src/Dockerfile.frontend
demo/
  ├── screenshots/
  ├── demo-video-link.txt
  └── live-demo-url.txt
presentation/
  └── slides.pdf
```

### MUST NOT Modify

- `src/backend/` — owned by Members 2 and 3
- `src/ml/` — owned by Member 3
- `docs/architecture.md` — owned by Member 1
- `AGENTS.md` — owned by Member 1
- Engine business logic
- Database schema
- API endpoint behavior

### Dependencies on Other Members

| Depends On | For What                                              |
|------------|-------------------------------------------------------|
| Member 2   | Working API endpoints to consume                      |
| Member 1   | API contracts (documents the API shape)               |
| Member 3   | Engine output shapes (for displaying explanations)    |

---

## Dependency Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                    PARALLEL DEVELOPMENT                           │
│                                                                   │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────────┐  │
│  │Member 1 │   │Member 2 │   │Member 3 │   │   Member 4      │  │
│  │  Docs   │   │ Backend │   │ Engines │   │   Frontend      │  │
│  │  MCP    │   │   API   │   │  ML/AI  │   │   Demo          │  │
│  │  Arch   │   │   DB    │   │  Tests  │   │   Presentation  │  │
│  └────┬────┘   └────┬────┘   └────┬────┘   └────────┬────────┘  │
│       │             │             │                   │           │
│       │      ┌──────┴──────┐     │                   │           │
│       │      │  Member 2   │     │                   │           │
│       │      │  calls      │◄────┘                   │           │
│       │      │  engine.run()│  (dict → dataclass)    │           │
│       │      └──────┬──────┘                         │           │
│       │             │                                │           │
│       │             │    REST API (/api/v1/*)         │           │
│       │             └────────────────────────────────►│           │
│       │                                              │           │
│       │         Integration contracts                │           │
│       └──────────────────────────────────────────────►│           │
│                                                       │           │
└───────────────────────────────────────────────────────────────────┘
```

### Execution Independence

| Member | Can Start Immediately | Blocked By              |
|--------|----------------------|-------------------------|
| 1      | ✅ Yes               | Nothing                 |
| 2      | ✅ Yes               | Engine signatures (M3)  |
| 3      | ✅ Yes               | Nothing                 |
| 4      | ⏳ Partially         | Working API (M2)        |

**Member 1 does NOT need to wait for Member 2 or 3** to begin:
- Architecture documentation
- Integration contract design
- MCP architecture design
- Governance rules (AGENTS.md)
- API contract documentation
- Team ownership documentation

Member 1 coordinates with Members 2 and 3 to ensure contracts
stay consistent with actual implementations.

---

## Integration Coordination Protocol

### When Contracts Change

1. Member 1 updates the relevant contract document.
2. Member 1 notifies affected members.
3. Affected members review and acknowledge.
4. Changes take effect after acknowledgment.

### When Implementation Diverges from Contract

1. The implementer (Member 2 or 3) documents the divergence.
2. Member 1 updates the contract to match the implementation.
3. Downstream members (especially Member 4) are notified.

### Conflict Resolution

If two members disagree on a boundary:
1. Check `AGENTS.md` for the governing rule.
2. Check the relevant contract document.
3. If still ambiguous, Member 1 (architecture lead) decides.
