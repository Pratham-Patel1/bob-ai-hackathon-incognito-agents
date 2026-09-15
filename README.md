# 🚀 SupplyChainOS — AI-Powered Supply Chain Resilience & Digital Twin Control Tower

> **Team**: Incognito Agents | **Track**: AI | **Hackathon**: IBM Bob AI Hackathon 2026

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | Incognito Agents |
| **Track** | AI |
| **Team Lead** | Mitesh Sunil Patil — 24dcs098@charusat.edu.in |
| **Members** | Jay Shirishbhai Patel, Nilay Rajeshbhai Patel, Pratham Shaileshbhai Patel |

---

## 🎯 Problem Statement

Supply-chain disruptions — weather events, port strikes, geopolitical crises — cascade across hundreds of active shipments in ways that are impossible to track manually. Fleet assets sit idle while routes are overloaded. Cold-chain shipments (vaccines, perishables) are especially vulnerable: a single temperature excursion can spoil $500K+ in cargo, but breaches are only discovered at delivery — too late to act.

---

## 💡 Solution

**SupplyChainOS** is an AI-powered supply chain resilience platform and Digital Twin Control Tower. It detects disruptions in real time, scores shipment risk using both deterministic rules and a trained ML model (RandomForest), monitors cold-chain temperature excursions, identifies idle/redeployable fleet assets, optimizes alternative routes, recommends carrier alternatives, simulates what-if scenarios via an in-memory Digital Twin, and governs all AI decisions through a human-in-the-loop approval workflow with a full immutable audit trail.

---

## ✨ Key Features

- **Disruption Intelligence**: Real-time detection of shipments affected by geographic/route disruptions with cascade impact scoring
- **AI Risk Scoring**: Deterministic multi-factor risk engine + RandomForest ML model predicting delay probability with explainable reasoning factors
- **Digital Twin Simulation**: In-memory what-if scenario modeling — compare baseline vs disrupted state without touching operational data
- **Human-in-the-Loop Governance**: 5-state recommendation lifecycle with human approval gate for high-value/critical decisions and full audit trail
- **Bob Copilot (MCP)**: Natural-language AI assistant powered by a local MCP server, dispatching structured tool calls to live backend data

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python 3.11, TypeScript |
| **Frameworks** | FastAPI, Next.js 14 (App Router) |
| **AI/ML** | scikit-learn (RandomForest), MCP (Model Context Protocol) |
| **IBM Technologies** | IBM Bob Copilot (local MCP integration) |
| **Databases** | PostgreSQL 16 (async SQLAlchemy) |
| **Other** | Docker, Docker Compose, Leaflet Maps, Recharts |

---

## 📁 Repository Structure

```
├── src/
│   ├── backend/           # FastAPI app (routers, engines, models, tests)
│   │   ├── engines/       # 11 pure-Python AI/ML engines
│   │   ├── mcp/           # MCP server + security + Bob Copilot
│   │   ├── routers/       # 35+ REST API endpoints
│   │   └── tests/         # 195+ pytest tests
│   ├── frontend/          # Next.js 14 Control Tower UI
│   └── docker-compose.yml
├── docs/                  # Architecture, API contracts, validation docs
├── demo/                  # Demo artifacts and screenshots
├── presentation/          # Slide deck
└── submission.yaml        # Structured submission metadata
```

---

## ⚡ How to Run

```bash
# 1. Clone the repo
git clone <repo-url>
cd bob-ai-hackathon-incognito-agents

# 2. Start all services (Docker required)
cd src
docker compose up --build

# 3. Seed the demo data (first run only)
docker compose exec backend python -m backend.data.seed

# 4. Access the application
#    Frontend Control Tower: http://localhost:3000
#    Backend API:            http://localhost:8000
#    API Docs:               http://localhost:8000/docs
```

See [docs/setup-guide.md](docs/setup-guide.md) for detailed setup instructions.

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | NOT DEPLOYED — run locally using docs/setup-guide.md |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/](presentation/) |
| 🎯 Demo Script | [See demo/demo-script.md](demo/demo-script.md) |

---

## ⚠️ Known Limitations

- **Authentication**: Actor field is a plain string — no OAuth/OIDC (development mode)
- **ML Training Data**: RandomForest trained on synthetic supply-chain data (realistic but not production data)
- **Cascade Depth**: Disruption cascade analysis limited to 2nd-order effects
- **Route Optimization**: Uses Haversine distance (no live OSRM/mapping service)
- **Bob Copilot**: Local MCP integration (no external watsonx cloud credentials configured)
- **Database**: Development credentials / exposed port (not production-hardened)

---

## 🏅 What We're Most Proud Of

The **complete end-to-end governance pipeline**: a disruption event triggers deterministic + ML risk scoring, generates an explainable recommendation with reasoning factors, routes to a human approval gate, and records every AI decision to an immutable audit trail — all in a single cohesive system. The **Digital Twin** lets operators safely simulate "what if this disruption were 3x worse?" without touching any operational state. The **Bob Copilot MCP integration** lets operators ask natural-language questions like "which shipments are at risk?" and receive structured, explainable answers backed by live backend data.

---

## 🧪 Test Coverage

- **Backend**: 195+ pytest tests (0 failures)
- **Coverage**: Disruption impact, shipment risk, ML prediction, cold chain, fleet intelligence, route optimization, carrier recommendation, cascade impact, digital twin, recommendation engine, human approval, audit trail, MCP security, Bob Copilot
