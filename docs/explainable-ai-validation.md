# Explainable AI & Decision Trace Validation Report

## Executive Summary
This document validates that SupplyChainOS provides transparent, traceable, and mathematically grounded explanations for all AI-assisted operational decisions. Every recommendation, risk diagnosis, route alternative, carrier selection, cold-chain anomaly assessment, and fleet assignment exposes the underlying data factors, feature contributions, and business logic without fabricated explanations.

---

## 1. Risk Explanation
The system evaluates operational delay and safety risks by combining two complementary engines:

1. **Deterministic Risk (`ShipmentRiskEngine`)**:
   - Scores risk across active weather disruptions, geographic proximity to storm epicenters, transit urgency, cargo value, cold-chain telemetry breaches, and carrier historical reliability.
   - Exposes explicit factor contributions with weights (e.g. `urgency (+0.38)`, `active_disruption (+0.45)`, `cold_chain_excursion (+0.25)`).
   - Generates human-readable diagnostic explanations summarizing primary driving indicators.

2. **Predictive Machine Learning Risk (`PredictiveRiskEngine`)**:
   - Generates delay probability inference using a pre-trained Random Forest model artifact (`risk_model.joblib`, version `1.0.0`).
   - Exposes the top feature importances (e.g. `ml_distance_to_epicenter_km`, `ml_carrier_reliability`, `ml_disruption_severity`).

3. **Combined Risk Weighting**:
   - **Formula**: `Combined Risk = 0.60 × Deterministic Score + 0.40 × ML Probability`
   - Clamped cleanly in `[0.0, 1.0]` and mapped to categorized risk tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).

---

## 2. Disruption Explanation
`DisruptionImpactEngine` determines impacted shipments by evaluating spatial and network corridor exposure:
- **Blast Radius & Geo Intersection**: Uses Haversine great-circle distance relative to disruption epicenter coordinates (`epicenter_lat`, `epicenter_lng`) and `affected_radius_km`.
- **Corridor Exposure**: Detects if shipment route codes match `affected_route_codes`.
- **Impact Classifications**: `geo_intersection`, `route_blocked`, or `both`.
- **Delay Estimation**: Base severity delay (Low: 4h, Medium: 12h, High: 24h, Critical: 48h) multiplied by exposure type + duration bonus for multi-day events.
- **Diagnostic Output**: Lists exact reasons why a consignment is classified as affected (e.g., *"Shipment is within 50 km of disruption (+10)"*, *"Critical severity disruption (+60)"*).

---

## 3. Route Explanation
`RouteOptimizationEngine` generates bypass routing options:
- **Disruption Avoidance**: Checks whether alternative corridor geometries avoid active disruption zones (+0.20 bonus).
- **Multi-Factor Scoring**: Evaluates distance (`km`), typical transit duration (`hours`), carrier mode suitability (`road`, `rail`, `air`, `sea`, `multimodal`), cost per kg, and historical reliability score.
- **Operational Reason**: Explains why the alternative route was selected (e.g., *"Bypasses active North Sea Gale perimeter; reduces transit time by 2.4h with 95% rail reliability"*).

---

## 4. Carrier Recommendation Explanation
`CarrierRecommendationEngine` ranks alternative freight carriers when current carriers are congested or disrupted:
- **Evaluation Criteria**: Carrier reliability rating (0.0 to 1.0), cost index relative to baseline, regional coverage match, and specialized capabilities (e.g. active refrigerated reefer equipment).
- **Operational Reason**: Details carrier code, cost differential, and capacity match (e.g., *"Switch to PTG-01 (PharmaTrans Global) — reliability 0.95, cost index 1.15, verified cold-chain coverage"*).

---

## 5. Cold Chain Explanation
`ColdChainAnomalyEngine` processes continuous IoT temperature sensor telemetry:
- **Boundary Verification**: Evaluates observed temperatures against target ranges (e.g., +2.0°C to +8.0°C for pharmaceuticals).
- **Excursion Severity Thresholds**:
  - **MINOR**: $\le 2.0^\circ\text{C}$ deviation **AND** $\le 15$ minutes duration.
  - **MAJOR**: $> 2.0^\circ\text{C}$ deviation **OR** $> 15$ minutes duration.
  - **CRITICAL**: $> 5.0^\circ\text{C}$ deviation **OR** $> 60$ minutes duration.
- **Explainable Actions**: Recommends prescriptive interventions (e.g., *"Critical temperature excursion: quarantine shipment immediately and inspect thermal battery pack"*).

---

## 6. Fleet Explanation
`FleetIntelligenceEngine` models vehicle utilization and redeployment suitability:
- **Capacity Telemetry**: Identifies idle units ($<20\%$ capacity utilization) and overloaded vehicles ($>95\%$).
- **Matching Constraints**: Evaluates vehicle load limit (`capacity_kg`), reefer capability (`temperature_capable`), and proximity to delayed/unassigned consignments.
- **Operational Reason**: Explains redeployment suitability (e.g., *"Reefer unit fl-01 stationed 14.2 km away with 4,500 kg excess capacity available for immediate transfer"*).

---

## 7. Cascade Explanation
`CascadingImpactEngine` models 1st-order downstream ripple effects:
- **Cascade Dimensions**:
  1. *Fleet Cascade*: Delayed vehicle cascading delays to subsequent scheduled shipments assigned to the same vehicle.
  2. *Carrier Cascade*: Overloaded carrier capacity cascading delays across connected logistics lanes.
- **Output Metrics**: Distinguishes direct shipment impact count vs. secondary cascade count, cumulative delay hours, and total secondary cargo value at risk ($).

---

## 8. Business Impact Explanation
`BusinessImpactEngine` translates operational delays into financial metrics:
- **Cargo Value at Risk**: Sum of invoice values for all affected direct and secondary consignments.
- **Holding & Demurrage Cost**: Evaluated at daily holding cost rates ($0.2\%/\text{day}$).
- **Contractual SLA Penalties**: Detects predicted arrival breaches against SLA buffer thresholds (default $4.0\text{h}$) and calculates financial penalty exposure ($\$5,000/\text{breach}$).
- **Total Financial Exposure**: Aggregates cargo risk + delay cost + SLA penalty exposure.

---

## 9. Recommendation Decision Trace
Every generated recommendation follows a deterministic, reproducible decision trace:

$$\text{Disruption} \longrightarrow \text{Impacted Shipments} \longrightarrow \text{Det Risk (60\%)} + \text{ML Risk (40\%)} \longrightarrow \text{Domain Optimization (Route/Carrier/Fleet/Cold-Chain)} \longrightarrow \text{Cascade \& Business Impact} \longrightarrow \text{Final Recommendation}$$

### Structured Reasoning Factors
Recommendations produce structured `reasoning_factors` payloads:
```json
[
  { "factor": "urgency", "value": 0.3806, "contribution": 0.3806, "weight": 0.6 },
  { "factor": "active_disruption", "value": 0.45, "contribution": 0.45, "weight": 0.6 },
  { "factor": "ml_distance_to_epicenter_km", "value": 42.5, "contribution": 0.28, "weight": 0.4 }
]
```
The frontend UI renders these factors as badges with clean string fallbacks, ensuring React objects are never rendered directly as React children.

---

## 10. AI Copilot Explainability
The natural-language AI Copilot routes queries through the Model Context Protocol (MCP) server layer without direct DB access. Operational queries for risk, routes, cold-chain, disruptions, simulations, and fleet return explanations sourced directly from engine outputs.

---

## 11. Human Approval & Safety Governance
- High-impact recommendations (cargo value $>\$50,000$ or critical disruption severity) mandate human approval.
- AI recommends; it cannot execute autonomous mutations.
- Approval requests without identified human operators are rejected at the governance boundary (`status="approval_required"`, `requires_human_approval=True`).

---

## 12. Audit Traceability
All approved and rejected recommendations commit an immutable record to PostgreSQL `decision_audit` table containing:
- `id` (UUID)
- `entity_type` (`recommendation`)
- `entity_id` (UUID of recommendation)
- `action` (`rec_approved` / `rec_rejected`)
- `actor` (Human operator name / ID)
- `actor_type` (`human`)
- `previous_state` & `new_state` (JSON snapshots)
- `reasoning` (Operator justification notes + AI diagnostic rationale)
- `created_at` (UTC timestamp)

---

## 13. Test Results

### Backend Test Suite (`pytest backend/tests/ -v`)
- **Total Passing Tests**: **195 / 195 tests** (100% pass rate).
- **Explainability Suite (`test_explainability.py`)**: 10 / 10 passed.
- **Copilot ↔ MCP Suite (`test_copilot.py`)**: 12 / 12 passed.
- **MCP Server Suite (`test_mcp.py`)**: 23 / 23 passed.
- **Domain Engine Unit Tests**: 150 / 150 passed.

### Frontend Production Build (`npm run build`)
- **Next.js Standalone Build**: Success (Exit code: `0`).
- **TypeScript Type Checking**: 0 errors.
- **Console / Hydration Check**: 0 errors.

---

## 14. Known Limitations
- **IBM Service Connection**: The local development environment operates in `SupplyChainOS-MCP-Live` mode; external IBM Bob / watsonx cloud endpoints are not configured.
- **Database Immutability**: Immutability is enforced at the application layer via state machine validation rather than PostgreSQL append-only cryptographic ledger extensions.
