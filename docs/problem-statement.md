# SupplyChainOS — Problem Statement

## 1. Executive Summary

Global supply chains are increasingly vulnerable to high-impact external disruptions—including extreme weather anomalies (cyclones, flash floods), geopolitical conflicts, port strikes, and critical infrastructure closures. In modern enterprise logistics, managing these disruptions is hampered by fragmented data silos, delayed human-in-the-loop triage, and an inability to forecast cascading operational and financial downstream consequences.

**SupplyChainOS** addresses the **L2 Supply Chain Disruption Assistant & Fleet Utilisation Optimizer** hackathon challenge by delivering an AI-powered Supply Chain Resilience & Digital Twin Control Tower that unifies multimodal supply chain telemetry, predicts delays, evaluates cold-chain temperature integrity, balances fleet capacity, and simulates mitigation alternatives before human managers commit to rerouting decisions.

---

## 2. The Four Root Operational Crises

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      THE FOUR CRITICAL FAILURE MODES                    │
├────────────────────────────────┬────────────────────────────────────────┤
│ 1. Disruption Invisibility    │ 2. Cascading Downstream Ripple         │
│ Weather, strike, road block     │ One delayed truck delays 3 downstream  │
│ manual cross-referencing lag.  │ shipments & warehouse cross-docks.     │
├────────────────────────────────┼────────────────────────────────────────┤
│ 3. Fleet Capacity Imbalance   │ 4. Cold-Chain Excursion Risk           │
│ 20% idle trucks in North,      │ Perishable / Pharma vaccines spoiled   │
│ 0 refrigerated reefers in South│ due to unnoticed temp deviation > 8°C. │
└────────────────────────────────┴────────────────────────────────────────┘
```

### 🔴 Problem 1: Disruption Detection Lag & Fragmented Telemetry
* **Pain Point**: When a sudden cyclone or highway closure strikes, logistics operators must manually cross-reference weather bulletins against hundreds of in-transit shipments across disparate carrier portals.
* **Impact**: Critical response time is lost during the initial golden hours of a disruption, turning minor reroutes into multi-day standstills.

### 🔴 Problem 2: Invisible Cascading Effects
* **Pain Point**: Logistics networks are tightly coupled graphs. A 12-hour delay on a primary corridor (Leg 1) prevents a specialized refrigerated vehicle from arriving on time for its next scheduled assignment (Leg 2), causing missed customer SLAs and cross-dock gridlocks.
* **Impact**: Secondary delays often cost 3x to 5x more than the initial disruption itself.

### 🔴 Problem 3: Fleet Geographical Imbalance & Low Utilization
* **Pain Point**: Fleets frequently experience severe geographical imbalances where trucks sit idle ($< 20\%$ utilization) in non-disrupted regions, while nearby critical hubs face acute vehicle shortages ($> 95\%$ overloaded).
* **Impact**: Substantial empty-haul miles (deadheading), excessive emergency spot-carrier surcharges, and lost asset efficiency.

### 🔴 Problem 4: Cold-Chain Telemetry Failures & Spoilage
* **Pain Point**: Temperature-sensitive cargo (pharmaceuticals, vaccines, fresh produce, biotech) requires strict storage bands ($2^\circ\text{C} - 8^\circ\text{C}$). Without real-time IoT anomaly detection, excursions are often only discovered at destination delivery.
* **Impact**: Millions in cargo write-offs, product loss, regulatory non-compliance, and life-critical supply stockouts.

---

## 3. The Core Challenge & Objectives

Traditional logistics solutions are **reactive and siloed**. Operators are presented with raw alerts without contextual risk scoring, delay predictions, or actionable alternatives.

### Target Objectives for SupplyChainOS:
1. **Automated Impact Detection**: Match geospatial disruption zones with active shipments and blocked routes within seconds.
2. **Unified Risk Scoring (60% Deterministic + 40% ML)**: Combine rule-based operational parameters with predictive machine learning to score disruption severity from 0 to 100.
3. **Continuous Cold-Chain Anomaly Auditing**: Classify IoT temperature deviations into `MINOR`, `MAJOR`, and `CRITICAL` excursions in real-time.
4. **Intelligent Asset & Route Optimization**: Match stranded cargo with idle/available fleet assets and evaluate ranked alternative routes based on safety, ETA, and cost.
5. **Zero-Risk Digital Twin Simulation**: Allow operations managers to test and simulate "what-if" rerouting scenarios in-memory before executing.
6. **Human-in-the-Loop Governance & Audit Trail**: Maintain human decision authority with clear `[APPROVE]` and `[REJECT]` actions backed by a complete compliance audit log.
