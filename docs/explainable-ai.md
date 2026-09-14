# SupplyChainOS — Explainable AI (XAI) Framework

> **Document Version**: 1.0.0  
> **Status**: ✅ IMPLEMENTED (Core Engine Explainability) / 📋 PLANNED (Copilot XAI Presentation)  
> **Author**: Member 1 — Enterprise Software Architect  
> **Target Audience**: AI Developers, Data Scientists, Logistics Operators, Compliance Officers  

---

## 1. Explainability Goals & Philosophy

In mission-critical enterprise supply chain management, "black box" machine learning predictions and automated recommendations are fundamentally unacceptable. Operators must not only know *what* risk level a shipment has, but *why* that risk was assigned and *which* factors contributed to the mitigation recommendation.

### Core XAI Principles in SupplyChainOS
1. **Dual-Layer Transparency**: Combines transparent deterministic rule calculations with feature-importance attribution from machine learning models.
2. **Dual-Format Output**: Every engine returns both **machine-readable structured vectors** (for algorithmic evaluation) and **human-readable textual explanations** (for operator dashboards and Bob Copilot).
3. **Audit Immutability**: All risk factors, weights, and recommendation reasons are persisted to the immutable `decision_audits` ledger upon decision generation.
4. **Actionable Justification**: Every recommendation includes the specific trade-offs (cost vs. time vs. disruption avoidance) that led to its selection.

---

## 2. Combined Risk Scoring Architecture

SupplyChainOS unifies deterministic rule-based domain logic with pre-trained RandomForest delay probability classification:

$$\text{Combined Risk Score} = 0.6 \times \text{Deterministic Score} + 0.4 \times \text{ML Predictive Score}$$

$$\text{Combined Score} = \begin{cases} 
0.6 \cdot S_{\text{det}} + 0.4 \cdot S_{\text{ml}} & \text{if ML artifact is available} \\
S_{\text{det}} & \text{if ML artifact is unavailable (Graceful Fallback)}
\end{cases}$$

```
┌────────────────────────────────────────────────────────────────────────┐
│                        COMBINED RISK COMPUTATION                       │
├───────────────────────────────────┬────────────────────────────────────┤
│  DETERMINISTIC ENGINE (60% Weight)│    MACHINE LEARNING (40% Weight)   │
│  • Disruption severity & proximity│    • RandomForestClassifier        │
│  • Arrival urgency (<24h / <48h)  │    • 8-feature normalized vector   │
│  • High-value cargo exposure      │    • Global feature importances    │
│  • Cold-chain active excursion    │    • Top 3 contributing features   │
│  • Carrier reliability baseline   │    • Probability of delay (class 1)│
└───────────────────┬───────────────┴────────────────────┬───────────────┘
                    │                                    │
                    ▼                                    ▼
       Deterministic Score [0.0, 1.0]          ML Delay Probability [0.0, 1.0]
                    │                                    │
                    └──────────────────┬─────────────────┘
                                       │
                                       ▼
                       Combined Score: [0.0, 1.0]
                                       │
                                       ▼
                       Risk Level: LOW / MED / HIGH / CRIT
```

### Risk Level Mapping Policy

| Score Range | Risk Level / Priority | Operational Meaning | System Action |
|---|---|---|---|
| **0.80 – 1.00** | 🔴 **CRITICAL** | Severe disruption, immediate SLA breach or cargo loss | Immediate expedite/reroute; mandatory supervisor approval |
| **0.60 – 0.79** | 🟠 **HIGH** | Significant delay projected; high financial exposure | Automated alternative route/carrier recommendation |
| **0.30 – 0.59** | 🟡 **MEDIUM** | Moderate disruption impact or minor schedule squeeze | Proactive monitoring; fleet/reroute suggestions |
| **0.00 – 0.29** | 🟢 **LOW** | Minor or zero impact; normal schedule variance | No recommendation generated; normal tracking |

---

## 3. Engine-by-Engine Explainability Specifications

Every pure engine in SupplyChainOS natively implements structured and natural language explainability.

```
┌────────────────────────────────────────────────────────────────────────┐
│                     ENGINE EXPLANATION SPECIFICATIONS                  │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Deterministic Shipment Risk (`ShipmentRiskEngine`)
- **Machine-Readable Structure**: `RiskResult.factors` (`list[RiskFactor]`)
  - `name: str` (e.g. `"disruption_severity"`, `"arrival_urgency"`, `"cargo_value"`)
  - `value: Any` (e.g. `"critical"`, `14.5`, `125000.0`)
  - `contribution: float` (e.g. `0.30`, `0.12`, `0.05`)
  - `weight: float`
- **Human-Readable Structure**: `RiskResult.explanation`
- **Example Explanation**:
  > *"High risk due to 1 critical disruption (+0.30), arrival in <24h (+0.12), cargo value >$100k (+0.05), carrier reliability 0.70 (+0.05)."*

---

### 3.2 Predictive Machine Learning Risk (`PredictiveRiskEngine`)
- **Machine-Readable Structure**: `MLRiskResult.top_features` (`list[FeatureContribution]`)
  - `feature_name: str` (e.g. `"days_to_scheduled_arrival"`, `"historical_route_delay_rate"`)
  - `value: float` (Raw feature value)
  - `importance: float` (Model feature importance weight)
- **Engine Feature Vector (8 Normalized Inputs)**:
  1. `days_to_scheduled_arrival`
  2. `historical_route_delay_rate`
  3. `carrier_reliability_score`
  4. `cargo_sensitivity_score`
  5. `simultaneous_disruption_count`
  6. `worst_disruption_severity_encoded`
  7. `hours_in_transit_pct`
  8. `weight_kg_normalized`
- **Example Structured Feature Output**:
```json
[
  { "feature": "days_to_scheduled_arrival", "value": 0.75, "importance": 0.32 },
  { "feature": "worst_disruption_severity_encoded", "value": 4.0, "importance": 0.28 },
  { "feature": "historical_route_delay_rate", "value": 0.15, "importance": 0.18 }
]
```

---

### 3.3 Recommendation Orchestrator (`RecommendationEngine`)
- **Machine-Readable Structure**: `RecommendationCandidate.reasoning_factors` (`list[dict]`)
  - Consolidates deterministic risk factors (`contribution > 0`) with ML top feature contributions (prefixed as `ml_<feature_name>` with weight `0.4`).
- **Human-Readable Structure**: `RecommendationCandidate.reason` and `RecommendationCandidate.description`
- **Example Explanation**:
  > *"Shipment TRK-1001 is rerouted via RT-CAPE (Cape of Good Hope Express) because the current route is affected by 'Red Sea Security Alert' (severity: critical, combined risk: 0.78). RT-CAPE has reliability 0.92 and avoids the disruption zone."*

---

### 3.4 Route Optimization (`RouteOptimizationEngine`)
- **Machine-Readable Structure**: `RouteOption.score`, `RouteOption.estimated_duration_hours`, `RouteOption.estimated_cost_usd`, `RouteOption.avoids_all_disruptions`
- **Human-Readable Structure**: `RouteOption.reason`
- **Formula**: $\text{score} = \text{reliability} - \text{distance\_penalty} - \text{cost\_penalty} + \text{disruption\_bonus}$
- **Example Explanation**:
  > *"Route RT-CAPE (Cape of Good Hope Route) reliability 0.90. avoids all active disruption zones. est. 96h, $6,250 total."*

---

### 3.5 Carrier Recommendation (`CarrierRecommendationEngine`)
- **Machine-Readable Structure**: `CarrierOption.score`, `CarrierOption.reliability_score`, `CarrierOption.cost_index`, `CarrierOption.covers_region`
- **Human-Readable Structure**: `CarrierOption.reason`
- **Formula**: $\text{score} = \frac{\text{reliability}}{\max(0.01, \text{cost\_index})} \times (\text{covers\_region} ? 1.0 : 0.6)$
- **Example Explanation**:
  > *"Carrier Cape Alternative Shipping — reliability 0.95, cost index 0.90 (10% below baseline), covers Rotterdam region."*

---

### 3.6 Fleet Intelligence (`FleetIntelligenceEngine`)
- **Machine-Readable Structure**: `RedeploymentSuggestion.distance_km`, `FleetAnalysis.utilization_histogram`
- **Human-Readable Structure**: `RedeploymentSuggestion.reason`
- **Example Explanation**:
  > *"Idle vehicle VH-IDLE-01 (refrigerated_truck) redeployed to shipment TRK-1002 (temperature_sensitive, 5000 kg). Distance: 45 km. Capacity utilization after: 42%."*

---

### 3.7 Cold-Chain Anomaly (`ColdChainAnomalyEngine`)
- **Machine-Readable Structure**: `AnomalyResult.has_excursion`, `AnomalyResult.severity`, `AnomalyResult.max_deviation_c`, `AnomalyResult.total_excursion_minutes`, `AnomalyResult.recommended_action`
- **Human-Readable Structure**: `AnomalyResult.explanation`
- **Example Explanation**:
  > *"Temperature exceeded 8.0°C by 3.4°C for 180 min (2 excursions). High risk of product degradation."*

---

### 3.8 Cascading Disruption Impact (`CascadingImpactEngine`)
- **Machine-Readable Structure**: `CascadeAnalysis.direct_count`, `CascadeAnalysis.secondary_count`, `CascadeAnalysis.total_value_at_risk_usd`, `CascadeAnalysis.cascade_chain`
- **Human-Readable Structure**: `CascadeAnalysis.explanation`
- **Example Explanation**:
  > *"2 shipments directly affected. 1 secondary shipments identified (1 fleet cascade, 0 carrier cascade). Total secondary cargo value at risk: $85,000."*

---

### 3.9 Business Financial Exposure (`BusinessImpactEngine`)
- **Machine-Readable Structure**: `BusinessImpact.total_cargo_value_at_risk_usd`, `BusinessImpact.cost_of_delay_usd`, `BusinessImpact.penalty_exposure_usd`, `BusinessImpact.sla_breach_count`
- **Human-Readable Structure**: `BusinessImpact.explanation`
- **Example Explanation**:
  > *"2 shipments affected. Total cargo value at risk: $240,000. Estimated cost of delay: $1,080. SLA breaches: 2 (penalty exposure: $10,000). Avg delay: 27.0h."*

---

### 3.10 Digital Twin What-If Simulation (`DigitalTwinEngine`)
- **Machine-Readable Structure**: `SimulationSummary` (All scenario aggregate fields), `SimulationResult.risk_scores`
- **Human-Readable Structure**: `SimulationResult.cascade_analysis.explanation` + `SimulationResult.business_impact.explanation`
- **Example Explanation**:
  > *"What-If scenario 'Typhoon Simulation' across 72h horizon: 4 shipments affected directly ($680,000 cargo value at risk). 1 secondary fleet cascade. Total delay cost: $8,500. 3 SLA breaches ($15,000 penalty exposure)."*

---

## 4. End-to-End Comprehensive Shipment Explanation Example

Below is an authentic JSON output representing the full, explainable audit package for a high-risk cold-chain shipment affected by a disruption:

```json
{
  "shipment_id": "shp-002",
  "tracking_number": "TRK-1002",
  "cargo": {
    "type": "temperature_sensitive",
    "description": "Biological Vaccines",
    "value_usd": 120000.0,
    "temperature_range_c": [2.0, 8.0]
  },
  "risk_assessment": {
    "deterministic_score": 0.85,
    "ml_predictive_score": 0.84,
    "combined_score": 0.846,
    "risk_level": "CRITICAL",
    "explanation": "Critical risk due to 1 critical disruption (+0.30), active cold-chain excursion (+0.25), urgent arrival <24h (+0.15), and high cargo value (+0.10).",
    "deterministic_factors": [
      { "name": "disruption_severity", "value": "critical", "contribution": 0.30, "weight": 1.0 },
      { "name": "cold_chain_excursion", "value": true, "contribution": 0.25, "weight": 1.0 },
      { "name": "arrival_urgency", "value": "<24h", "contribution": 0.15, "weight": 1.0 },
      { "name": "cargo_value", "value": 120000.0, "contribution": 0.10, "weight": 1.0 }
    ],
    "ml_top_features": [
      { "feature": "days_to_scheduled_arrival", "value": 0.75, "importance": 0.32 },
      { "feature": "cargo_sensitivity_score", "value": 1.0, "importance": 0.26 },
      { "feature": "worst_disruption_severity_encoded", "value": 4.0, "importance": 0.22 }
    ]
  },
  "cold_chain_analysis": {
    "has_excursion": true,
    "severity": "CRITICAL",
    "max_deviation_c": 3.4,
    "total_excursion_minutes": 180,
    "recommended_action": "EXPEDITE_IMMEDIATELY",
    "explanation": "Temperature exceeded 8.0°C by 3.4°C for 180 min (2 excursions). High risk of product degradation."
  },
  "recommendation": {
    "type": "expedite",
    "priority": "critical",
    "title": "Expedite TRK-1002 — cold-chain excursion",
    "reason": "Shipment TRK-1002 requires expedited delivery: active temperature excursion detected on temperature-sensitive cargo (cargo value: $120,000). Disruption 'Red Sea Alert' increases excursion risk.",
    "requires_approval": true,
    "estimated_savings_usd": 6000.0,
    "reasoning_factors": [
      { "factor": "disruption_severity", "value": "critical", "contribution": 0.30, "weight": 1.0 },
      { "factor": "cold_chain_excursion", "value": true, "contribution": 0.25, "weight": 1.0 },
      { "factor": "ml_days_to_scheduled_arrival", "value": 0.75, "contribution": 0.32, "weight": 0.4 }
    ]
  }
}
```

---

## 5. Current Implementation vs. Future XAI Roadmap

| XAI Capability | Current Implementation (MVP) | Future Production Roadmap (Phase 4) |
|---|---|---|
| **Global Feature Importance** | Static `feature_importances_` from trained RandomForest artifact | TreeSHAP (SHapley Additive exPlanations) for exact local per-prediction attribution |
| **Deterministic Explanations** | Rule-based string formatting with factor contributions | Dynamic natural language synthesis via watsonx.ai Granite LLM |
| **Counterfactual Analysis** | In-memory Digital Twin what-if scenario simulations | Automated counterfactual generator (*"What minimum speed increase avoids SLA breach?"*) |
| **Interactive Sensitivity** | Static top-3 feature contribution list | Interactive what-if feature sliders in Next.js control tower UI |
| **Audit Provenance** | JSONB metadata in PostgreSQL `decision_audits` | Cryptographically signed provenance chains for regulatory compliance |
