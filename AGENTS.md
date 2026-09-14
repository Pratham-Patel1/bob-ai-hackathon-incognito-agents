# AGENTS.md — SupplyChainOS Project Instructions

> Persistent instructions for AI coding agents working on this repository.
> **Read this file in full before making ANY changes.**

---

## 1. Project Purpose

**SupplyChainOS** is an AI-powered supply-chain control tower built for the
IBM Bob AI Innovation Hackathon (track: AI).

It detects disrupted shipments, calculates risk, predicts delays, detects
cold-chain temperature excursions, identifies idle fleet assets, optimizes
routes, recommends carriers, analyses cascading disruption impact, simulates
what-if scenarios via a Digital Twin, estimates business impact, generates
actionable recommendations, requires human approval for high-value operations,
and maintains a full audit trail.

---

## 2. Architecture Overview

```
Frontend (Next.js 14)
       ↓ REST
Backend (FastAPI + async SQLAlchemy + asyncpg)
       ↓ plain dicts
Pure Python Engines (src/backend/engines/)
       ↓
PostgreSQL (via SQLAlchemy — routers only)
```

- **Frontend**: Next.js 14 App Router, Leaflet maps, Recharts.
- **Backend**: FastAPI, Python 3.12+, async SQLAlchemy, asyncpg.
- **Database**: PostgreSQL 16.
- **AI/ML**: scikit-learn, offline-trained RandomForest artifact (joblib).
- **Infrastructure**: Docker, Docker Compose.
- **MCP / Bob Copilot**: Phase 2 integration layer — NOT yet implemented.

---

## 3. Technology Stack

| Layer       | Technology                                    |
|-------------|-----------------------------------------------|
| Frontend    | Next.js 14, TypeScript, Leaflet, Recharts     |
| Backend API | FastAPI, Pydantic, Uvicorn                    |
| ORM         | async SQLAlchemy 2.x, asyncpg                 |
| Database    | PostgreSQL 16                                 |
| AI/ML       | scikit-learn, joblib, numpy                   |
| Containers  | Docker, Docker Compose                        |
| Validation  | pytest (engines + seed data)                  |

---

## 4. Team Ownership

| Member | Role                              | Primary Directories                            |
|--------|-----------------------------------|------------------------------------------------|
| 1      | Architecture, MCP, Copilot, docs  | `AGENTS.md`, `docs/`, `CONTEXT.md`             |
| 2      | Backend, DB, API, schemas, Docker | `src/backend/routers/`, `models/`, `schemas/`, `data/`, `database.py`, `docker-compose.yml` |
| 3      | AI/ML, engines, training          | `src/backend/engines/`, `src/ml/`              |
| 4      | Frontend, demo, presentation      | `src/frontend/`, `demo/`, `presentation/`      |

**Rule:** Do NOT implement another member's responsibilities without explicit instruction.

---

## 5. Directory Ownership

```
bob-ai-hackathon-incognito-agents/
├── AGENTS.md                    # Member 1 — governance
├── CONTEXT.md                   # Member 1 — project context
├── CONTRIBUTING.md              # Template — DO NOT DELETE
├── README.md                    # Shared — update as needed
├── submission.yaml              # Shared — DO NOT RENAME
├── docs/                        # Member 1 — architecture & docs
│   ├── architecture.md
│   ├── team-ownership.md
│   ├── integration-contracts.md
│   ├── api-contracts.md
│   ├── problem-statement.md
│   ├── solution-overview.md
│   └── setup-guide.md
├── src/
│   ├── backend/
│   │   ├── config.py            # Member 2 — settings
│   │   ├── database.py          # Member 2 — DB engine/session
│   │   ├── main.py              # Member 2 — FastAPI app factory
│   │   ├── models/              # Member 2 — SQLAlchemy models
│   │   ├── schemas/             # Member 2 — Pydantic schemas
│   │   ├── routers/             # Member 2 — API endpoints
│   │   ├── data/                # Member 2 — seed data
│   │   ├── utils/               # Member 2 — audit helpers, geo
│   │   ├── engines/             # Member 3 — PURE PYTHON ONLY
│   │   └── tests/               # Members 2 + 3
│   ├── ml/                      # Member 3 — training, features, artifacts
│   ├── docker-compose.yml       # Member 2
│   ├── Dockerfile.backend       # Member 2
│   └── Dockerfile.frontend      # Member 4
├── demo/                        # Member 4 — screenshots, video
└── presentation/                # Member 4 — slide deck
```

---

## 6. Engine Purity Rule (CRITICAL)

All files under `src/backend/engines/` **must remain pure Python**.

### Engines MUST NOT import:
- `fastapi` (or any sub-module)
- `sqlalchemy` (or any sub-module)
- Database session objects (`AsyncSession`, `Session`)
- HTTP request/response objects (`Request`, `Response`)
- `backend.database`
- `backend.config`

### Engines receive:
- Plain Python `dict` objects (converted from ORM models in the router)
- Primitive types (`str`, `int`, `float`, `bool`, `list`, `datetime`)

### Engines return:
- Python `dataclass` objects (defined in the engine file itself)
- No side effects — no DB writes, no HTTP calls, no file I/O

### Why:
The router layer is responsible for:
1. Loading data from the database → converting to dicts
2. Calling the engine with those dicts
3. Persisting any results back to the database
4. Writing audit records

This separation ensures engines are testable without a running database
and keeps business logic decoupled from infrastructure.

---

## 7. Database Rules

- **Schema ownership**: Member 2 owns all SQLAlchemy models.
- **DO NOT modify database schema** unless explicitly approved by the team.
- **DO NOT add new tables** without explicit approval.
- Tables are auto-created at startup via `Base.metadata.create_all`.
- Seed data runs only in `development` or `demo` environments.
- Use `uuid.UUID` for all primary keys.
- All timestamps use `datetime` with UTC timezone.

---

## 8. API Rules

- All API endpoints live under `/api/v1/`.
- Routers are registered in `src/backend/main.py`.
- Use Pydantic schemas for request/response validation.
- Use `async def` for all endpoint handlers.
- Use `Depends(get_async_db)` for database sessions.
- Write audit records for state-changing operations.
- **DO NOT invent APIs that are not documented** in `docs/api-contracts.md`.
- Human approval endpoints must enforce the state machine:
  `pending → approved → implemented` or `pending → rejected/deferred`.

---

## 9. Testing Rules

- Engine tests live in `src/backend/tests/`.
- Tests run with `pytest` from `src/`.
- **DO NOT remove existing tests.**
- **New functionality MUST include appropriate tests.**
- Engine tests must NOT require a running database.
- Use plain dicts as engine inputs in tests (mirror what routers provide).
- Test file naming: `test_<engine_name>.py`.
- Existing tests: `test_disruption_impact.py`, `test_shipment_risk.py`,
  `test_cold_chain.py`, `test_fleet_intelligence.py`, `test_cascade_impact.py`,
  `test_geo.py`, `test_seed_data.py`.

---

## 10. Security Rules

- **DO NOT expose secrets in source code.**
- All secrets go in `.env` (never committed — listed in `.gitignore`).
- Environment variable template: `src/.env.example`.
- API keys for watsonx.ai: `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`.
- Database credentials are environment variables, not hardcoded.
- CORS origins are configurable via `CORS_ORIGINS` env var.

---

## 11. MCP / Bob Copilot Rules

- MCP is a **Phase 2 integration layer** — NOT yet implemented.
- Do NOT claim MCP is implemented.
- MCP design must use the existing engine contracts.
- MCP tools will map to existing API endpoints.
- MCP will NOT bypass the approval state machine.
- Bob Copilot integration will consume MCP tool outputs.

---

## 12. Change-Control Rules

- All changes must be traceable via git commits.
- Do not force-push or rewrite shared history.
- Do not modify `.github/workflows/validate.yml`.
- Do not rename `submission.yaml`.
- Do not delete required template files:
  `CONTRIBUTING.md`, `docs/problem-statement.md`, `docs/solution-overview.md`,
  `docs/architecture.md`, `docs/setup-guide.md`.

---

## 13. Forbidden Actions

> **Hard rules. Violating these will break the project.**

| # | Forbidden Action |
|---|------------------|
| 1 | Do NOT modify database schema unless explicitly approved |
| 2 | Do NOT create duplicate engines (one engine per concern) |
| 3 | Do NOT put FastAPI or SQLAlchemy inside engines |
| 4 | Do NOT implement another member's responsibilities without explicit instruction |
| 5 | Do NOT silently change approved business rules (thresholds, weights, etc.) |
| 6 | Do NOT remove existing tests |
| 7 | Do NOT train ML models during application startup |
| 8 | Do NOT introduce unnecessary infrastructure (Redis, Kafka, queues, Neo4j, microservices) |
| 9 | Do NOT invent APIs that are not documented |
| 10 | Do NOT expose secrets in source code |
| 11 | Do NOT modify `.github/workflows/validate.yml` |
| 12 | Do NOT rename or delete `submission.yaml` |
| 13 | Do NOT add dependencies without documenting them in `requirements.txt` |
| 14 | Do NOT use `sync` database access — all DB operations are `async` |

---

## 14. Currently Implemented vs Planned

### IMPLEMENTED (exists in repo and is functional)

**Engines** (all pure Python, all in `src/backend/engines/`):
- `DisruptionImpactEngine` — identifies shipments affected by a disruption
- `ShipmentRiskEngine` — deterministic weighted-sum risk scoring
- `PredictiveRiskEngine` — ML-based delay probability (loads pre-trained artifact)
- `ColdChainAnomalyEngine` — temperature excursion detection
- `FleetIntelligenceEngine` — idle/overloaded detection + redeployment
- `RouteOptimizationEngine` — rank alternative routes
- `CarrierRecommendationEngine` — rank alternative carriers
- `CascadingImpactEngine` — first-order cascading impact analysis
- `DigitalTwinEngine` — in-memory what-if simulation
- `BusinessImpactEngine` — financial exposure calculation
- `RecommendationEngine` — orchestrator for all engines

**API Routers** (all mounted under `/api/v1/`):
- Health, Shipments, Disruptions, Fleet, Recommendations, Simulation, Audit, Carriers, Routes

**ML Training Pipeline** (`src/ml/`):
- Feature extraction, training data generation, model training, evaluation

**Database**:
- Full schema (9 models), seed data, async session management

**Tests**:
- 7 test files covering engines and seed data

### PLANNED (not yet implemented)

- MCP server and Bob Copilot integration
- Next.js 14 frontend (Dockerfile exists but commented out)
- watsonx.ai integration
- Slack notifications

---

## 15. Validation (CI)

The only CI check is `.github/workflows/validate.yml` (DO NOT MODIFY).

Required files:
- `README.md`, `submission.yaml`
- `docs/problem-statement.md`, `docs/solution-overview.md`, `docs/architecture.md`, `docs/setup-guide.md`
- `demo/demo-video-link.txt`

`submission.yaml` rules:
- `team.track` must be exactly `AI`, `DevOps`, `Sustainability`, or `Open`
- All string values must use double quotes
- `problem_statement` and `solution_summary` use YAML block scalars (`>`)

---

## 16. Quick Reference

```bash
# Run backend locally (requires PostgreSQL)
cd src && docker compose up db -d
cd src && uvicorn backend.main:app --reload

# Run all tests (no DB required for engine tests)
cd src && pytest

# Run full stack
cd src && docker compose up --build

# API docs
http://localhost:8000/docs
```
