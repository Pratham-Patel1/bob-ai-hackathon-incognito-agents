# SupplyChainOS — Judge-Facing Demo Script

> **Duration**: ~8–10 minutes
> **Prerequisites**: Application running (`docker compose up`) with seeded demo data
> **URLs**: Frontend http://localhost:3000 | API Docs http://localhost:8000/docs

---

## 🎬 Demo Narrative

*"SupplyChainOS is an AI-powered supply chain control tower. Let me walk you through how an operator responds to an active disruption — from detection all the way through human-approved execution and audit."*

---

## Step 1 — Open Control Tower

**Action**: Navigate to `http://localhost:3000`

**Show**:
- KPI metrics bar at the top (total shipments, active disruptions, at-risk count, fleet idle count)
- Interactive map with shipment markers and disruption zones highlighted
- Summary: "We have 200 active shipments, 3 live disruptions, and the system has already identified which ones are affected."

---

## Step 2 — Show Active Disruption

**Action**: Click "Disruptions" in the navigation or view the map disruption overlay

**Show**:
- List of 3 active disruptions (e.g., port strike, weather event, route closure)
- Disruption severity, affected region, start time
- Say: *"This port strike in [region] is our highest severity event."*

---

## Step 3 — Show Affected Shipments

**Action**: Select the active disruption → view impacted shipments list

**Show**:
- List of affected shipments with impact scores
- Geographic overlap + route intersection detection
- Say: *"The system has automatically identified which shipments pass through or near this disruption zone."*

---

## Step 4 — Assess a High-Risk Shipment

**Action**: Click on the highest-risk affected shipment (risk score ≥ 0.7)

**Show**:
- Shipment details panel: origin, destination, current leg, cargo type
- Risk score prominently displayed
- Say: *"Shipment SHP-001 has a risk score of 0.84 — that's our most critical."*

---

## Step 5 — Explain Deterministic + ML Risk

**Action**: Open the shipment risk assessment (click "Assess Risk" or view the risk panel)

**Show**:
- **Deterministic factors**: weather severity, port congestion, route distance, SLA time remaining
- **ML prediction**: RandomForest model delay probability (e.g., 78%)
- **Reasoning factors list**: ordered by contribution weight
- Say: *"The risk combines a rules-based score with a machine learning prediction. The top factor is 'port_congestion_index: 0.91' — the ML model agrees this is high-risk."*

---

## Step 6 — Show Cold-Chain Excursion

**Action**: Navigate to "Cold Chain" section

**Show**:
- Temperature telemetry timeline for a cold-chain shipment (e.g., vaccine/pharma cargo)
- A temperature excursion breach highlighted (e.g., +4°C above threshold for 47 minutes)
- Excursion alert with cargo value at risk ($)
- Say: *"This pharmaceutical shipment had a temperature breach. The system flagged it 47 minutes into the excursion — before delivery failure."*

---

## Step 7 — Show Idle/Redeployable Fleet

**Action**: Navigate to "Fleet" section

**Show**:
- Fleet assets categorized: idle trucks, overloaded vessels, available containers
- Idle asset with current location and redeployment distance
- Say: *"We have 3 idle trucks within 200km of the disrupted route — the fleet intelligence engine identified them as redeployable."*

---

## Step 8 — Show Alternative Route

**Action**: In the recommendations panel or map, show route alternatives for the affected shipment

**Show**:
- Current blocked route vs. 2–3 alternative routes
- Distance, estimated delay delta, and risk score for each
- Say: *"Route B adds only 340km but avoids the disruption zone entirely, reducing estimated delay from 72h to 8h."*

---

## Step 9 — Show Carrier Recommendation

**Action**: View carrier recommendations for the disrupted shipment

**Show**:
- Ranked carrier list with cost, reliability score, capacity availability
- Top recommended carrier highlighted
- Say: *"FastFreight Logistics has 94% on-time reliability and available capacity — the system scores it highest among 5 alternatives."*

---

## Step 10 — Generate/View Recommendation

**Action**: Navigate to "Recommendations" panel — show a generated recommendation or click "Generate"

**Show**:
- Recommendation card: action type (reroute/carrier switch), priority (CRITICAL/HIGH), estimated savings
- Status badge: PENDING APPROVAL (for high-value items) or AUTO-EXECUTABLE
- Say: *"The recommendation engine generated: 'Reroute SHP-001 via Route B using FastFreight — estimated $42,000 SLA penalty avoided.'"*

---

## Step 11 — Show Explainable Reasoning Factors

**Action**: Click "View Details" on the recommendation

**Show**:
- Reasoning factors rendered as a list/table (e.g., `route_risk_delta`, `carrier_reliability`, `sla_exposure_usd`, `cold_chain_risk`)
- Each factor with its weight/value
- Say: *"The system doesn't just say 'do this' — it explains exactly why, with every factor scored and ranked."*

---

## Step 12 — Run Digital Twin Scenario

**Action**: Navigate to "Simulation" (Digital Twin Studio)

**Show**:
- Scenario configuration: select disruption, adjust severity (e.g., 2× worse), add a second disruption
- Click "Run Simulation"
- Say: *"The Digital Twin lets us ask: what if this disruption were twice as severe? It runs completely in-memory — zero changes to operational data."*

---

## Step 13 — Compare Baseline vs Simulated Impact

**Action**: View simulation results

**Show**:
- Side-by-side: Baseline metrics vs Simulated metrics
- Delta: affected shipments (+12), financial exposure (+$180K), cold-chain risk (+3 shipments)
- Say: *"In the simulated scenario, 12 additional shipments fall into high-risk — giving us time to pre-position fleet before a crisis escalates."*

---

## Step 14 — Show Human Approval Gate

**Action**: Return to Recommendations panel — click on the PENDING APPROVAL recommendation

**Show**:
- Approval requirement explanation: "This action exceeds $50,000 in operational cost — requires supervisor authorization"
- Approval form with actor name field and approve/reject/override options
- Say: *"The system never autonomously executes high-value decisions. It requires a human supervisor to explicitly approve."*

---

## Step 15 — Approve Using Human Actor

**Action**: Enter actor name (e.g., "ops-supervisor-demo") → click "Approve"

**Show**:
- Recommendation status transitions: PENDING → APPROVED
- Success confirmation
- Say: *"The human has authorized execution. The actor name is recorded — this is the governance layer."*

---

## Step 16 — Show Audit Trail

**Action**: Navigate to "Audit" section

**Show**:
- Audit log entries in reverse-chronological order
- The just-approved recommendation entry: timestamp, actor, action, recommendation ID, outcome
- Say: *"Every AI decision and human action is recorded immutably. This audit trail is read-only — it cannot be edited or deleted."*

---

## Step 17 — Ask Bob Copilot a Natural-Language Question

**Action**: Navigate to "Copilot" section (Bob Copilot chat interface)

**Type**: `"Which shipments are currently at highest risk and why?"`

**Show**:
- Bob receives the query
- Say: *"Bob Copilot is our natural-language interface. Instead of navigating dashboards, operators can just ask."*

---

## Step 18 — Show MCP Tool Dispatch

**Action**: Observe the response generation (or show from response metadata)

**Show**:
- Bob dispatched MCP tool: `get_high_risk_shipments` → backend API → live data
- Tool call visible in response metadata or explain from docs
- Say: *"Bob doesn't hallucinate. It dispatches a structured MCP tool call to our live backend API, gets real data, then formulates the answer."*

---

## Step 19 — Show Explainable Response

**Action**: View Bob's completed response

**Show**:
- Structured answer: top 3 shipments with risk scores and key factors
- Each claim traceable to actual backend data
- Say: *"The response is explainable and grounded — every claim is backed by the same engine that powers the dashboard."*

---

## Step 20 — Conclude with Business Impact

**Speak**:

*"Let me summarize the business impact:*

- *A port strike was detected in real time — 23 affected shipments identified automatically*
- *ML risk scoring identified 4 critical shipments within seconds*
- *A cold-chain breach was caught 47 minutes early — preventing $500K in spoilage*
- *The Digital Twin showed a 2× escalation would expose $180K additional risk — letting us pre-position fleet*
- *One supervisor approval governed the AI recommendation — with a full audit trail*
- *Bob Copilot answered the operator's question in natural language using live data*

*SupplyChainOS turns supply chain disruptions from crises into managed events."*

---

## 🔑 Key Demo Data References

| Entity | ID/Name | Notes |
|---|---|---|
| High-risk shipment | First shipment with risk_score ≥ 0.7 in recommendations | Use seeded data |
| Active disruption | Any of the 3 seeded disruptions | Port strike preferred for demo |
| Cold-chain excursion | Cold-chain shipment with temperature breach | In cold chain telemetry |
| Idle fleet asset | Any asset with status=IDLE | In fleet panel |
| Pending approval rec | Any recommendation with requires_approval=true | In recommendations panel |

---

## ⚠️ Demo Safety Rules

- **DO NOT** use destructive endpoints (DELETE operations)
- **DO NOT** modify the database schema or seed data during demo
- **DO NOT** claim external IBM cloud integration if not configured
- The Digital Twin runs in-memory — clicking "Run Simulation" is safe
- Approving one recommendation for demo purposes is acceptable — it is recorded in audit
