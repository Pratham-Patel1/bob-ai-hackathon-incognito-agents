# SupplyChainOS — Engine Integration Contracts

> **Version**: 1.0.0 | **Last Updated**: 2026-09-14
> Defines stable contracts between backend routers and pure Python engines.

---

## Purpose

This document defines the **input/output contracts** for every engine in
SupplyChainOS. These contracts allow Member 2 (backend/API) and Member 3
(engines) to develop in parallel with confidence that integration will work.

### Contract Flow

```
Member 2 (Backend/API)           Member 3 (Engines)
     │                                │
     │  1. Load data from DB          │
     │  2. Convert to dicts           │
     │                                │
     └──── dict inputs ──────────────►│
                                      │  3. Apply business logic
     ◄──── dataclass output ──────────┘
     │
     │  4. Persist results to DB
     │  5. Write audit record
     │  6. Serialize to JSON response
     │
     └──── JSON ──────────────────────► Member 4 (Frontend)
                                        Member 1 (MCP / Copilot)
```

### Status Legend

| Label         | Meaning                                      |
|---------------|----------------------------------------------|
| ✅ IMPLEMENTED | Code exists and is functional in the repo    |
| 📋 PLANNED     | Contract defined but not yet implemented     |

---

## 1. DisruptionImpactEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/disruption_impact.py`
**Owner**: Member 3
**Purpose**: Identify all shipments affected by a given disruption.

### Input

```python
def run(
    disruption: dict[str, Any],
    shipments: list[dict[str, Any]],
) -> ImpactResult
```

**`disruption` dict keys**:
| Key                    | Type          | Required | Description                           |
|------------------------|---------------|----------|---------------------------------------|
| `id`                   | `str | UUID`  | ✅       | Disruption ID                         |
| `epicenter_lat`        | `float`       | ✅       | Epicenter latitude                    |
| `epicenter_lng`        | `float`       | ✅       | Epicenter longitude                   |
| `affected_radius_km`   | `float`       | ✅       | Radius of impact zone in km           |
| `affected_route_codes` | `list[str]`   | ✅       | Route codes blocked by disruption     |
| `severity`             | `str`         | ✅       | `low` \| `medium` \| `high` \| `critical` |
| `start_time`           | `datetime`    | Optional | Start of disruption                   |
| `estimated_end_time`   | `datetime`    | Optional | Estimated end of disruption           |

**`shipments` list item dict keys**:
| Key            | Type          | Required | Description                           |
|----------------|---------------|----------|---------------------------------------|
| `id`           | `str | UUID`  | ✅       | Shipment ID                           |
| `current_lat`  | `float | None`| Optional | Current latitude                      |
| `current_lng`  | `float | None`| Optional | Current longitude                     |
| `route_code`   | `str | None`  | Optional | Current route code                    |
| `cargo_type`   | `str`         | Optional | `general` \| `temperature_sensitive` \| `hazmat` |
| `status`       | `str`         | Optional | `in_transit` \| `at_risk` \| `delayed` |

### Output

```python
@dataclass
class ImpactedShipment:
    shipment_id: str
    impact_reason: str              # geo_intersection | route_blocked | both
    distance_to_epicenter_km: float | None
    impact_score: int               # 0–100
    impact_level: str               # LOW | MEDIUM | HIGH | CRITICAL
    estimated_delay_hours: float
    factors: list[str]              # Human-readable explanation strings

@dataclass
class ImpactResult:
    disruption_id: str
    affected_count: int
    impacted_shipments: list[ImpactedShipment]
```

### Error Behavior
- Returns `ImpactResult` with `affected_count=0` and empty `impacted_shipments` if no matches.
- Invalid coordinates are silently skipped (no exception).

### Side Effects
- None. Pure function.

### Dependencies
- None (contains its own `haversine` function).

### API Integration Point
- `POST /api/v1/disruptions` — auto-triggers on disruption creation
- `GET /api/v1/disruptions/{id}/impact` — on-demand analysis

### Explainability Fields
- `factors`: list of human-readable strings (e.g., `"High severity disruption (+45)"`)
- `impact_level`: categorical summary

---

## 2. ShipmentRiskEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/shipment_risk.py`
**Owner**: Member 3
**Purpose**: Deterministic weighted-sum risk scoring for a single shipment.

### Input

```python
def run(
    shipment: dict[str, Any],
    active_disruptions: list[dict[str, Any]],
    temperature_excursion: bool = False,
    carrier: dict[str, Any] | None = None,
) -> RiskResult
```

**`shipment` dict keys**:
| Key                    | Type          | Required | Description                            |
|------------------------|---------------|----------|----------------------------------------|
| `scheduled_arrival`    | `datetime|str`| Optional | Expected arrival time                  |
| `cargo_value_usd`     | `float`       | Optional | Cargo value in USD                     |
| `temperature_required`| `bool`        | Optional | Whether cold-chain monitoring needed   |

**`active_disruptions` list item dict keys**:
| Key        | Type   | Required | Description                                |
|------------|--------|----------|--------------------------------------------|
| `severity` | `str`  | Optional | `low` \| `medium` \| `high` \| `critical` |

**`carrier` dict keys**:
| Key                 | Type    | Required | Description                   |
|---------------------|---------|----------|-------------------------------|
| `reliability_score` | `float` | Optional | 0.0–1.0 reliability rating    |

### Output

```python
@dataclass
class RiskFactor:
    name: str
    value: float
    contribution: float         # actual contribution to total score
    weight: float               # defined weight for this factor

@dataclass
class RiskResult:
    score: float                # 0.0–1.0
    level: str                  # low | medium | high | critical
    factors: list[RiskFactor]
    explanation: str            # Human-readable summary
```

### Risk Factors and Weights

| Factor               | Weight | Trigger Condition                     |
|----------------------|--------|---------------------------------------|
| `active_disruption`  | 0.30   | Any active disruption linked          |
| `compound_disruptions`| 0.10  | More than 1 active disruption         |
| `urgency`            | 0.20   | <24h to scheduled arrival             |
| `high_value_cargo`   | 0.15   | cargo_value_usd > $100,000           |
| `cold_chain_excursion`| 0.20  | temperature_required + excursion      |
| `carrier_reliability`| 0.10   | reliability_score < 0.7               |

### Error Behavior
- Gracefully handles missing/None fields with defaults.
- Score clamped to [0.0, 1.0].

### Side Effects
- None. Pure function.

### Dependencies
- None.

### API Integration Point
- `GET /api/v1/shipments/{id}/risk`
- `POST /api/v1/shipments/bulk-risk-refresh`

### Explainability Fields
- `explanation`: e.g., `"Risk score 0.65 (high). Top factors: active disruption (+0.27), urgency (+0.18)"`
- `factors`: full breakdown with name, value, contribution, weight

---

## 3. PredictiveRiskEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/predictive_risk.py`
**Owner**: Member 3
**Purpose**: ML-based delay probability prediction.

### Input

```python
def run(
    shipment: dict[str, Any],
    active_disruptions: list[dict[str, Any]],
    carrier: dict[str, Any],
) -> MLRiskResult
```

**Input dicts**: Same shape as ShipmentRiskEngine inputs plus additional
feature extraction keys (see `src/ml/features.py` for full list).

### Output

```python
@dataclass
class FeatureContribution:
    feature_name: str
    value: float
    importance: float

@dataclass
class MLRiskResult:
    ml_score: float | None          # None if model unavailable
    top_features: list[FeatureContribution]
    model_version: str
```

### Error Behavior
- Returns `MLRiskResult(ml_score=None)` if:
  - Model artifact not found (`risk_model.joblib`)
  - Feature extraction module unavailable
  - Any runtime error during inference
- Never raises exceptions.

### Side Effects
- Loads model artifact once at module import (not at each call).
- No other side effects.

### Dependencies
- `joblib` — model deserialization
- `numpy` — feature arrays
- `src/ml/features.py` — feature extraction

### API Integration Point
- `GET /api/v1/shipments/{id}/risk` (called alongside ShipmentRiskEngine)
- Combined score: `0.6 × deterministic + 0.4 × ML` (configurable via env)

### Explainability Fields
- `top_features`: top 3 features by importance with names and values
- `model_version`: identifies the trained artifact version

---

## 4. ColdChainAnomalyEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/cold_chain.py`
**Owner**: Member 3
**Purpose**: Temperature excursion detection and severity classification.

### Input

```python
def run(
    temperature_logs: list[dict[str, Any]],
    temp_min_c: float,
    temp_max_c: float,
    polling_interval_minutes: float = 5.0,
) -> ColdChainAnalysis
```

**`temperature_logs` list item dict keys**:
| Key              | Type          | Required | Description                    |
|------------------|---------------|----------|--------------------------------|
| `temperature_c`  | `float`       | ✅       | Recorded temperature in Celsius|
| `recorded_at`    | `str|datetime`| Optional | Timestamp of reading           |

### Output

```python
@dataclass
class ExcursionWindow:
    start_idx: int
    end_idx: int
    max_deviation_c: float
    duration_minutes: float
    severity: str               # minor | major | critical

@dataclass
class ColdChainAnalysis:
    has_excursion: bool
    severity: str               # none | minor | major | critical
    excursion_count: int
    max_deviation_c: float
    total_excursion_minutes: float
    recommended_action: str     # Human-readable action
    explanation: str
    excursion_windows: list[ExcursionWindow]
```

### Severity Classification

| Severity   | Deviation          | Duration           |
|------------|--------------------|--------------------|
| `minor`    | ≤ 2°C              | ≤ 15 min           |
| `major`    | 2–5°C OR           | 15–60 min          |
| `critical` | > 5°C OR           | > 60 min           |

### Error Behavior
- Returns `ColdChainAnalysis(has_excursion=False)` if no logs provided.

### Side Effects
- None. Pure function.

### Dependencies
- None.

### API Integration Point
- `GET /api/v1/shipments/{id}/temperature`

### Explainability Fields
- `recommended_action`: severity-specific action (e.g., "Quarantine cargo on arrival")
- `explanation`: summary with excursion count, severity, deviation, duration

---

## 5. FleetIntelligenceEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/fleet_intelligence.py`
**Owner**: Member 3
**Purpose**: Idle/overloaded vehicle detection and redeployment suggestions.

### Input — Fleet Analysis

```python
def analyse_fleet(
    fleet: list[dict[str, Any]],
) -> FleetAnalysis
```

**`fleet` list item dict keys**:
| Key                | Type          | Required | Description                    |
|--------------------|---------------|----------|--------------------------------|
| `id`               | `str | UUID`  | ✅       | Fleet vehicle ID               |
| `status`           | `str`         | Optional | `active` \| `maintenance` \| etc. |
| `utilization_pct`  | `float`       | Optional | 0–100 utilization percentage   |
| `current_lat`      | `float`       | Optional | Current latitude               |
| `current_lng`      | `float`       | Optional | Current longitude              |

### Output — Fleet Analysis

```python
@dataclass
class FleetAnalysis:
    idle_count: int
    overloaded_count: int
    idle_vehicle_ids: list[str]
    overloaded_vehicle_ids: list[str]
    utilization_histogram: dict[str, int]   # "0-20": N, "20-50": N, etc.
```

### Thresholds
- **Idle**: `utilization_pct < 20%` AND `status == "active"`
- **Overloaded**: `utilization_pct > 95%`

### Input — Redeployment Suggestions

```python
def suggest_redeployments(
    fleet: list[dict[str, Any]],
    needy_shipments: list[dict[str, Any]],
) -> list[RedeploymentSuggestion]
```

**`needy_shipments` list item dict keys**:
| Key                    | Type          | Required | Description                 |
|------------------------|---------------|----------|-----------------------------|
| `id`                   | `str | UUID`  | ✅       | Shipment ID                 |
| `current_lat`          | `float`       | Optional | Current latitude            |
| `current_lng`          | `float`       | Optional | Current longitude           |
| `weight_kg`            | `float`       | Optional | Shipment weight             |
| `cargo_type`           | `str`         | Optional | Cargo type                  |
| `temperature_required` | `bool`        | Optional | Cold-chain flag             |
| `tracking_number`      | `str`         | Optional | Human-readable tracking ID  |

### Output — Redeployment Suggestions

```python
@dataclass
class RedeploymentSuggestion:
    vehicle_id: str
    target_shipment_id: str
    distance_km: float
    reason: str                 # Human-readable explanation
```

### Matching Logic
- Matches each idle vehicle to the nearest needy shipment by haversine distance.
- Respects capacity constraint (`weight_kg ≤ capacity_kg`).
- Respects temperature constraint (`temperature_required → temperature_capable`).

### Error Behavior
- Returns empty list if no idle vehicles or no needy shipments.

### Side Effects
- None. Pure function.

### Dependencies
- `utils.geo.haversine` (imported via sys.path)

### API Integration Point
- `GET /api/v1/fleet/redeployment-suggestions`
- `GET /api/v1/fleet/idle`
- `GET /api/v1/fleet/overloaded`

### Explainability Fields
- `reason`: includes vehicle ID, shipment tracking number, distance, capacity utilization

---

## 6. RouteOptimizationEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/route_optimizer.py`
**Owner**: Member 3
**Purpose**: Rank alternative routes for a disrupted shipment.

### Input

```python
def run(
    shipment: dict[str, Any],
    active_disruptions: list[dict[str, Any]],
    available_routes: list[dict[str, Any]],
    top_n: int = 3,
) -> list[RouteOption]
```

**`shipment` dict keys**:
| Key                    | Type   | Required | Description                    |
|------------------------|--------|----------|--------------------------------|
| `origin`               | `str`  | Optional | Origin location                |
| `destination`          | `str`  | Optional | Destination location           |
| `weight_kg`            | `float`| Optional | Shipment weight                |
| `temperature_required` | `bool` | Optional | Cold-chain requirement         |
| `route_id`             | `str`  | Optional | Current route ID (to exclude)  |

**`active_disruptions` list item dict keys**:
| Key                    | Type        | Required | Description                    |
|------------------------|-------------|----------|--------------------------------|
| `affected_route_codes` | `list[str]` | Optional | Route codes blocked            |

**`available_routes` list item dict keys**:
| Key                      | Type    | Required | Description                  |
|--------------------------|---------|----------|------------------------------|
| `id`                     | `str`   | ✅       | Route ID                     |
| `code`                   | `str`   | Optional | Route code                   |
| `name`                   | `str`   | Optional | Route name                   |
| `origin`                 | `str`   | Optional | Route origin                 |
| `destination`            | `str`   | Optional | Route destination            |
| `distance_km`            | `float` | Optional | Distance                     |
| `typical_duration_hours` | `float` | Optional | Expected transit time        |
| `cost_per_kg_usd`        | `float` | Optional | Cost per kg                  |
| `reliability_score`      | `float` | Optional | 0.0–1.0 reliability         |
| `active`                 | `bool`  | Optional | Whether route is available   |

### Output

```python
@dataclass
class RouteOption:
    route_id: str
    route_code: str
    route_name: str
    score: float                    # Composite score
    estimated_duration_hours: float
    estimated_cost_usd: float
    avoids_all_disruptions: bool
    reason: str                     # Human-readable explanation
```

### Scoring Formula
`score = reliability - distance_penalty - cost_penalty + disruption_bonus`
- `disruption_bonus = 0.2` if route avoids all active disruption zones
- Sorted by: avoids_all first, then score descending

### Error Behavior
- Returns empty list if no matching routes found.

### Side Effects
- None. Pure function.

### Dependencies
- None.

### API Integration Point
- Called internally by `RecommendationEngine.run()` for reroute recommendations
- Also via `GET /api/v1/routes/{id}/alternatives` (Member 2 reference query, not engine)

### Explainability Fields
- `reason`: includes route code, reliability, disruption avoidance, duration, cost

---

## 7. CarrierRecommendationEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/carrier_recommender.py`
**Owner**: Member 3
**Purpose**: Rank alternative carriers for a disrupted shipment.

### Input

```python
def run(
    shipment: dict[str, Any],
    current_carrier: dict[str, Any],
    all_carriers: list[dict[str, Any]],
    active_disruptions: list[dict[str, Any]],
    top_n: int = 3,
) -> list[CarrierOption]
```

**`current_carrier` dict keys**:
| Key  | Type   | Required | Description              |
|------|--------|----------|--------------------------|
| `id` | `str`  | ✅       | Current carrier ID       |

**`all_carriers` list item dict keys**:
| Key                 | Type          | Required | Description                  |
|---------------------|---------------|----------|------------------------------|
| `id`                | `str`         | ✅       | Carrier ID                   |
| `name`              | `str`         | Optional | Carrier name                 |
| `code`              | `str`         | Optional | Carrier code                 |
| `reliability_score` | `float`       | Optional | 0.0–1.0 reliability          |
| `cost_index`        | `float`       | Optional | Cost relative to baseline    |
| `coverage_regions`  | `list[str]`   | Optional | Regions this carrier covers  |
| `active`            | `bool`        | Optional | Whether carrier is active    |

**`active_disruptions` list item dict keys**:
| Key               | Type   | Required | Description                  |
|-------------------|--------|----------|------------------------------|
| `affected_region` | `str`  | Optional | Region affected by disruption|

### Output

```python
@dataclass
class CarrierOption:
    carrier_id: str
    carrier_name: str
    carrier_code: str
    score: float                # reliability / cost_index
    reliability_score: float
    cost_index: float
    covers_region: bool
    reason: str                 # Human-readable explanation
```

### Filtering
- Excludes current carrier.
- Excludes carriers with coverage regions overlapping disrupted regions.
- Penalizes carriers that don't cover the destination (score × 0.6).

### Error Behavior
- Returns empty list if no suitable carriers found.

### Side Effects
- None. Pure function.

### Dependencies
- None.

### API Integration Point
- Called internally by `RecommendationEngine.run()` for carrier_change recommendations

### Explainability Fields
- `reason`: includes carrier name, reliability, cost index, region coverage

---

## 8. CascadingImpactEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/cascade_impact.py`
**Owner**: Member 3
**Purpose**: First-order cascading disruption impact analysis.

### Input

```python
def run(
    direct_shipment_ids: set[str],
    all_shipments: list[dict[str, Any]],
    fleet: list[dict[str, Any]],
) -> CascadeAnalysis
```

**`all_shipments` list item dict keys**:
| Key                    | Type          | Required | Description                  |
|------------------------|---------------|----------|------------------------------|
| `id`                   | `str | UUID`  | ✅       | Shipment ID                  |
| `tracking_number`      | `str`         | Optional | Tracking number              |
| `fleet_id`             | `str | None`  | Optional | Assigned fleet vehicle       |
| `carrier_id`           | `str | None`  | Optional | Assigned carrier             |
| `cargo_value_usd`      | `float`       | Optional | Cargo value                  |
| `status`               | `str`         | Optional | Shipment status              |

### Output

```python
@dataclass
class CascadeNode:
    shipment_id: str
    tracking_number: str
    level: int                      # 1 = secondary
    impact_type: str                # fleet_cascade | carrier_cascade
    caused_by_shipment_id: str
    estimated_delay_hours: float

@dataclass
class CascadeAnalysis:
    direct_count: int
    secondary_count: int
    cascade_chain: list[CascadeNode]
    total_value_at_risk_usd: float
    total_delay_hours_estimate: float
    explanation: str
```

### Cascade Paths

1. **Fleet cascade**: Delayed vehicle → other in-transit shipments on same vehicle.
   Conservative delay estimate: 12 hours.

2. **Carrier cascade**: If >30% of a carrier's active capacity is directly affected,
   flag other in-transit shipments on that carrier. Delay estimate: 6 hours.

### Error Behavior
- Returns `CascadeAnalysis(secondary_count=0)` if no cascading effects found.

### Side Effects
- None. Pure function (Python graph traversal, no Neo4j).

### Dependencies
- None.

### API Integration Point
- `GET /api/v1/disruptions/{id}/cascade`
- Called internally by `RecommendationEngine.run()`

### Explainability Fields
- `explanation`: summary including direct/secondary counts, fleet/carrier breakdown, total value

---

## 9. BusinessImpactEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/business_impact.py`
**Owner**: Member 3
**Purpose**: Translate delay estimates into financial exposure.

### Input

```python
def run(
    affected_shipments: list[dict[str, Any]],
    daily_holding_cost_rate: float = 0.002,
    sla_buffer_hours: float = 4.0,
    sla_penalty_usd: float = 5000.0,
) -> BusinessImpact
```

**`affected_shipments` list item dict keys**:
| Key                  | Type              | Required | Description                  |
|----------------------|-------------------|----------|------------------------------|
| `id`                 | `str | UUID`      | ✅       | Shipment ID                  |
| `tracking_number`    | `str`             | Optional | Tracking number              |
| `cargo_value_usd`    | `float`           | Optional | Cargo value in USD           |
| `scheduled_arrival`  | `datetime | str`  | Optional | Expected arrival             |
| `estimated_arrival`  | `datetime | str`  | Optional | Estimated actual arrival     |

### Output

```python
@dataclass
class ShipmentImpact:
    shipment_id: str
    tracking_number: str
    cargo_value_usd: float
    delay_hours: float
    cost_of_delay_usd: float
    sla_breach: bool
    penalty_exposure_usd: float

@dataclass
class BusinessImpact:
    total_cargo_value_at_risk_usd: float
    total_delay_hours: float
    avg_delay_hours: float
    cost_of_delay_usd: float
    penalty_exposure_usd: float
    sla_breach_count: int
    shipment_breakdown: list[ShipmentImpact]
    explanation: str
```

### Business Rules
- `cost_of_delay = (delay_hours / 24) × cargo_value × daily_holding_cost_rate`
- `sla_breach = delay_hours > sla_buffer_hours`
- `penalty = sla_penalty_usd if sla_breach else 0`

### Error Behavior
- Handles missing dates gracefully (delay = 0).

### Side Effects
- None. Pure function.

### Dependencies
- None.

### API Integration Point
- Called internally by `RecommendationEngine.run()` and `DigitalTwinEngine.run()`

### Explainability Fields
- `explanation`: summary with shipment count, total value, delay cost, SLA breaches

---

## 10. RecommendationEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/recommendation_engine.py`
**Owner**: Member 3
**Purpose**: Orchestrator — calls all engines and generates prioritized recommendations.

### Input

```python
def run(
    disruption: dict[str, Any],
    all_shipments: list[dict[str, Any]],
    all_routes: list[dict[str, Any]],
    all_carriers: list[dict[str, Any]],
    all_fleet: list[dict[str, Any]],
    temperature_excursions: dict[str, bool],
    carriers_by_id: dict[str, dict[str, Any]],
    approval_threshold_usd: float = 50_000.0,
) -> OrchestratorResult
```

### Output

```python
@dataclass
class RecommendationCandidate:
    shipment_id: str | None
    disruption_id: str | None
    type: str                   # reroute | carrier_change | fleet_redeploy | hold | expedite | escalate
    priority: str               # low | medium | high | critical
    title: str
    description: str
    reason: str                 # Enforced non-empty
    reasoning_factors: list[dict]
    alternative_route_id: str | None
    alternative_carrier_id: str | None
    estimated_savings_usd: float
    estimated_delay_reduction_hours: float
    requires_approval: bool

@dataclass
class OrchestratorResult:
    recommendations: list[RecommendationCandidate]
    impact_result: ImpactResult | None
    cascade_result: CascadeAnalysis | None
    business_impact_result: BusinessImpact | None
    affected_shipment_ids: list[str]
```

### Recommendation Generation Rules
- Only generates recommendations for shipments with combined risk ≥ 0.3.
- Reroute: generated when alternative routes exist.
- Carrier change: generated when combined risk ≥ 0.5 and alternatives exist.
- Expedite: generated for cold-chain excursions on temperature-sensitive cargo.
- Fleet redeploy: generated for idle vehicles matching delayed shipments.
- Escalate: generated when cascading secondary impacts are detected.

### Approval Rules
- `requires_approval = True` when:
  - `cargo_value > approval_threshold_usd` OR
  - `disruption_severity == "critical"` OR
  - `type == "fleet_redeploy"` OR
  - Carrier cost increase > 20%

### Error Behavior
- Returns empty `OrchestratorResult` if no shipments are impacted.

### Side Effects
- None. Pure function.

### Dependencies
- All other engines (disruption_impact, shipment_risk, predictive_risk,
  cold_chain, fleet_intelligence, route_optimizer, carrier_recommender,
  cascade_impact, business_impact).

### API Integration Point
- `POST /api/v1/recommendations/generate?disruption_id=...`

### Explainability Fields
- `reason`: per-recommendation explanation including tracking number, risk score, disruption title
- `reasoning_factors`: list of dicts with `factor`, `value`, `contribution`, `weight`

---

## 11. DigitalTwinEngine ✅ IMPLEMENTED

**File**: `src/backend/engines/digital_twin.py`
**Owner**: Member 3
**Purpose**: In-memory what-if scenario simulation using the full engine pipeline.

### Input

```python
def run(
    scenario: dict[str, Any],
    all_shipments: list[dict[str, Any]],
    all_routes: list[dict[str, Any]],
    all_carriers: list[dict[str, Any]],
    all_fleet: list[dict[str, Any]],
    temperature_excursions: dict[str, bool],
    carriers_by_id: dict[str, dict[str, Any]],
    approval_threshold_usd: float = 50_000.0,
) -> SimulationResult
```

**`scenario` dict keys**:
| Key                    | Type        | Required | Description                      |
|------------------------|-------------|----------|----------------------------------|
| `name`                 | `str`       | Optional | Scenario title                   |
| `disruption_type`      | `str`       | Optional | `weather` \| `geopolitical` \| etc. |
| `severity`             | `str`       | Optional | `low` \| `medium` \| `high` \| `critical` |
| `epicenter_lat`        | `float`     | ✅       | Hypothetical epicenter latitude  |
| `epicenter_lng`        | `float`     | ✅       | Hypothetical epicenter longitude |
| `affected_radius_km`   | `float`     | Optional | Impact radius (default: 100)     |
| `affected_route_codes` | `list[str]` | Optional | Hypothetical blocked routes      |
| `horizon_hours`        | `float`     | Optional | Simulation horizon (default: 72) |

### Output

```python
@dataclass
class SimulationSummary:
    scenario_name: str
    disruption_type: str
    disruption_severity: str
    affected_radius_km: float
    horizon_hours: float
    total_affected_shipments: int
    total_secondary_shipments: int
    total_cargo_value_at_risk_usd: float
    total_cost_of_delay_usd: float
    penalty_exposure_usd: float
    sla_breach_count: int
    recommendation_count: int

@dataclass
class SimulationResult:
    summary: SimulationSummary
    affected_shipments: list[dict]
    risk_scores: dict[str, float]       # shipment_id → combined score
    cascade_analysis: CascadeAnalysis | None
    business_impact: BusinessImpact | None
    top_recommendations: list[dict]     # Serialized for JSON
```

### Key Property
- Uses the SAME engines as the live pipeline.
- Builds a hypothetical disruption dict in memory (NOT persisted).
- No shipment state is modified.
- The router writes exactly ONE audit record for traceability.

### Error Behavior
- Returns `SimulationResult` with zero counts if no shipments affected.

### Side Effects
- None from the engine. The ROUTER writes one audit record.

### Dependencies
- `recommendation_engine` (full pipeline)
- `shipment_risk`
- `predictive_risk`

### API Integration Point
- `POST /api/v1/simulation/run`

### Explainability Fields
- `summary`: complete scenario-level metrics
- `top_recommendations`: up to 10 recommendations with type, priority, title, reason
