# SupplyChainOS — Solution Overview

## 1. System Vision

**SupplyChainOS** is an intelligent, multi-stage resilience platform and Digital Twin control tower designed to transform reactive supply chain operations into proactive, automated, and explainable decision workflows.

By combining deterministic domain engines, predictive Machine Learning, IoT sensor analytics, multi-objective optimization, and an interactive Digital Twin simulator, SupplyChainOS empowers operations teams to mitigate disruptions before cargo is delayed or lost.

---

## 2. End-to-End Decision Pipeline

SupplyChainOS executes a structured 13-stage decision pipeline:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SUPPLYCHAINOS PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
 1. DATA INGESTION                    ▼
    Shipments | Disruptions | Routes | Carriers | Fleet | IoT Sensor Logs
                                      │
 2. DISRUPTION DETECTION              ▼
    DisruptionImpactEngine: Geo-spatial intersection + Route block detection
                                      │
 3. OPERATIONAL RISK ASSESSMENT       ▼
    ShipmentRiskEngine: 60% Deterministic (value, deadline, severity) + 40% ML
                                      │
 4. PREDICTIVE ML MODEL               ▼
    PredictiveRiskEngine: Random Forest delay probability & hour estimation
                                      │
 5. SPECIALIZED TELEMATICS            ▼
    ├── ColdChainAnomalyEngine: Excursion severity (Minor / Major / Critical)
    └── FleetIntelligenceEngine: Idle (<20%) vs Overloaded (>95%) asset matching
                                      │
 6. MULTI-OBJECTIVE OPTIMIZATION      ▼
    ├── RouteOptimizationEngine: Disruption-avoiding ranked corridors
    └── CarrierRecommendationEngine: Historical reliability + spot rate ranking
                                      │
 7. SYSTEM SIMULATION & IMPACT        ▼
    ├── CascadingImpactEngine: Downstream ripple (Graph Depth = 1)
    ├── Digital Twin Simulator: In-memory comparative what-if scenario testing
    └── BusinessImpactEngine: Financial exposure & SLA penalty savings
                                      │
 8. UNIFIED RECOMMENDATION            ▼
    RecommendationEngine: Synthesizes single optimal [Route + Carrier + Vehicle]
                                      │
 9. HUMAN-IN-THE-LOOP CONTROL         ▼
    Control Tower Dashboard: Manager [APPROVE] or [REJECT]
                                      │
10. AUDIT TRAIL & COMPLIANCE          ▼
    DecisionAudit Log: Immutable record of timestamp, model version, and user
```

---

## 3. Core Architectural Modules

### 🔬 Disruption & Risk Intelligence (Phase 2A)
* **DisruptionImpactEngine**: Preserves high-precision bounding-box geo-spatial intersection and route code matching, calculating base impact scores and explainable factors.
* **ShipmentRiskEngine**: Bridges deterministic business logic (cargo value, priority, hazardous materials) with empirical Machine Learning predictions.

### 🤖 Predictive Analytics & Telematics (Phase 2B & 2C)
* **PredictiveRiskEngine**: Pre-trained Random Forest model (`risk_model.joblib`) performing sub-millisecond offline inference to predict transit delay likelihood.
* **ColdChainAnomalyEngine**: Continuous temperature boundary analysis ($2^\circ\text{C} - 8^\circ\text{C}$) alerting on critical excursions to prevent perishable cargo loss.
* **FleetIntelligenceEngine**: Real-time vehicle telematics monitoring capacity utilization and identifying nearby refrigerated assets for rapid redeployment.

### ⚡ Optimization & Digital Twin (Phase 2D & 2E)
* **Route & Carrier Optimizer**: Evaluates trade-offs across safety, transit time, and transportation cost to generate ranked options.
* **CascadingImpactEngine**: Graph traversal evaluating downstream vehicle and schedule ripple effects up to Depth 1.
* **Digital Twin Simulator**: Safely runs what-if simulations entirely in memory without touching production database state.

### 🛡️ Human-in-the-Loop & Audit Governance (Phase 2F & 3)
* **RecommendationEngine**: Generates a unified action bundle complete with human-readable rationale.
* **Manager Governance**: Clear approval gates ensure autonomous systems assist human operators rather than replacing accountability.
* **DecisionAudit**: Full regulatory compliance and operational traceability recorded for every decision.

---

## 4. IBM Bob & Model Context Protocol (MCP) Copilot Integration

SupplyChainOS exposes its intelligence layer to AI assistants (including IBM Bob) through the **Model Context Protocol (MCP)**:

```text
┌──────────────────┐
│   IBM Bob / AI   │
│   Agent Copilot  │
└────────┬─────────┘
         │ Natural Language Query: "What is the impact of Disruption D10 on Cold Chain?"
         ▼
┌──────────────────┐
│    MCP Server    │ (src/backend/mcp/server.py)
└────────┬─────────┘
         │ Structured Tool Invocations
         ├─────────────────────────────┬────────────────────────────┐
         ▼                             ▼                            ▼
┌──────────────────┐          ┌──────────────────┐         ┌──────────────────┐
│ get_disruption_  │          │ check_cold_chain │         │ simulate_what_if │
│   impact_tool    │          │      _tool       │         │    _route_tool   │
└────────┬─────────┘          └────────┬─────────┘         └────────┬─────────┘
         │                             │                            │
         └─────────────────────────────┼────────────────────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │ FastAPI Backend (/api/v1/...) │
                       └───────────────┬───────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │      SupplyChainOS DB         │
                       └───────────────────────────────┘
```

Through this integration, managers can interactively interrogate the control tower via natural language while maintaining rigorous deterministic validation under the hood.
