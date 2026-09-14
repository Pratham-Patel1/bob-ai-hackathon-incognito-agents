# SupplyChainOS — System Architecture & Technical Specifications

## 1. System Overview

SupplyChainOS is engineered as a decoupled, layered micro-modular architecture consisting of:
1. **PostgreSQL Database** with Async SQLAlchemy & asyncpg connection pooling.
2. **FastAPI Backend Gateway** providing schema-validated REST APIs.
3. **Pure Python Computational Engines** executing deterministic analytics, ML inference, and optimization.
4. **Model Context Protocol (MCP) Server** exposing supply chain intelligence tools to IBM Bob and AI agent copilots.
5. **Next.js 14 Control Tower Frontend** delivering real-time map visualizations and human-in-the-loop decision approval.

---

## 2. Layered Architecture Diagram

```mermaid
graph TD
    subgraph UI_Layer["Presentation Layer (Member 4)"]
        FE["Next.js 14 Control Tower Dashboard"]
        MAP["Leaflet Geospatial Map"]
        CHARTS["Recharts Cold-Chain & Risk Charts"]
        APPROVAL["Human-in-the-Loop Approval UI"]
    end

    subgraph Agent_Layer["AI & Copilot Layer (Member 1)"]
        BOB["IBM Bob / LLM Copilot"]
        MCP["FastMCP Server (src/backend/mcp/)"]
    end

    subgraph API_Layer["API Gateway Layer (Member 2)"]
        FASTAPI["FastAPI REST API (/api/v1/)"]
        ROUTERS["Routers: Shipments, Disruptions, Fleet, Audit, Simulations"]
        SCHEMAS["Pydantic v2 Request/Response Validation"]
    end

    subgraph Engine_Layer["Intelligence & ML Layer (Member 3)"]
        E_DISRUPT["DisruptionImpactEngine"]
        E_RISK["ShipmentRiskEngine"]
        E_ML["PredictiveRiskEngine (Random Forest)"]
        E_COLD["ColdChainAnomalyEngine"]
        E_FLEET["FleetIntelligenceEngine"]
        E_ROUTE["RouteOptimizationEngine"]
        E_CARRIER["CarrierRecommendationEngine"]
        E_CASCADE["CascadingImpactEngine"]
        E_TWIN["DigitalTwinEngine (In-Memory)"]
        E_REC["RecommendationEngine"]
    end

    subgraph Data_Layer["Data & Persistence Layer (Member 2)"]
        PG[(PostgreSQL 16 Database)]
        MODELS["SQLAlchemy Models"]
        SEED["Seed Data Fixtures"]
    end

    FE --> FASTAPI
    BOB --> MCP
    MCP --> FASTAPI
    FASTAPI --> SCHEMAS
    FASTAPI --> ROUTERS
    ROUTERS --> MODELS
    ROUTERS --> Engine_Layer
    MODELS --> PG
```

---

## 3. Database Entity Relationship Model

```mermaid
erDiagram
    SHIPMENT ||--o{ SHIPMENT_DISRUPTION : "tracked in"
    DISRUPTION ||--o{ SHIPMENT_DISRUPTION : "causes"
    SHIPMENT }o--|| ROUTE : "assigned to"
    SHIPMENT }o--|| CARRIER : "transported by"
    SHIPMENT ||--o{ TEMPERATURE_LOG : "monitored by"
    SHIPMENT ||--o{ RECOMMENDATION : "receives"
    RECOMMENDATION ||--o{ DECISION_AUDIT : "logs"
    FLEET }o--o{ SHIPMENT : "allocates"

    SHIPMENT {
        uuid id PK
        string tracking_number
        string origin
        string destination
        string cargo_type
        float cargo_value
        string priority
        datetime deadline
        boolean temperature_sensitive
        boolean is_hazmat
        string status
    }

    DISRUPTION {
        uuid id PK
        string title
        string disruption_type
        string severity
        float latitude
        float longitude
        float radius_km
        datetime start_time
        datetime estimated_end_time
    }

    SHIPMENT_DISRUPTION {
        uuid id PK
        uuid shipment_id FK
        uuid disruption_id FK
        string impact_level
        float impact_score
        float estimated_delay_hours
    }

    TEMPERATURE_LOG {
        uuid id PK
        uuid shipment_id FK
        datetime timestamp
        float temperature_celsius
        float humidity_percent
    }

    FLEET {
        uuid id PK
        string vehicle_code
        string vehicle_type
        float capacity_tons
        float current_load_tons
        boolean is_refrigerated
        float latitude
        float longitude
        string status
    }

    RECOMMENDATION {
        uuid id PK
        uuid shipment_id FK
        string recommended_action
        uuid target_route_id
        uuid target_carrier_id
        uuid target_vehicle_id
        string status
        jsonb reasons
        jsonb business_impact
    }

    DECISION_AUDIT {
        uuid id PK
        uuid recommendation_id FK
        uuid shipment_id FK
        string action_taken
        string approver
        datetime timestamp
        string model_version
    }
```

> [!IMPORTANT]
> The many-to-many relationship between `Shipment` and `Disruption` is maintained via `shipment_disruptions`. Never add a direct `shipment.disruption_id` column.

---

## 4. API Endpoints & Contracts Specification

| Endpoint | Method | Input Parameters | Return Schema | Target Engine |
| :--- | :--- | :--- | :--- | :--- |
| `/api/v1/health` | GET | None | `{"status": "ok"}` | System Check |
| `/api/v1/shipments` | GET | `status`, `priority`, `limit`, `offset` | `List[ShipmentResponse]` | CRUD |
| `/api/v1/shipments/{id}` | GET | `id: UUID` | `ShipmentDetailResponse` | CRUD |
| `/api/v1/disruptions` | GET | `severity`, `limit` | `List[DisruptionResponse]` | CRUD |
| `/api/v1/disruptions/{id}/impact` | GET | `id: UUID` | `DisruptionImpactReportResponse` | `DisruptionImpactEngine` |
| `/api/v1/shipments/{id}/risk` | GET | `id: UUID` | `ShipmentRiskResponse` | `ShipmentRiskEngine` |
| `/api/v1/shipments/{id}/prediction` | GET | `id: UUID` | `PredictiveRiskResponse` | `PredictiveRiskEngine` |
| `/api/v1/shipments/{id}/cold-chain` | GET | `id: UUID` | `ColdChainAnalysisResponse` | `ColdChainAnomalyEngine` |
| `/api/v1/fleet/intelligence` | GET | `min_capacity`, `is_refrigerated` | `FleetIntelligenceResponse` | `FleetIntelligenceEngine` |
| `/api/v1/simulations/route` | POST | `SimulationRequest` | `SimulationComparisonResponse` | `DigitalTwinEngine` |
| `/api/v1/recommendations` | GET | `status: Enum` | `List[RecommendationResponse]` | `RecommendationEngine` |
| `/api/v1/recommendations/{id}/approve` | POST | `DecisionNotesRequest` | `ApprovalStateResponse` | State Machine + Audit |
| `/api/v1/recommendations/{id}/reject` | POST | `RejectionReasonRequest` | `ApprovalStateResponse` | State Machine + Audit |
| `/api/v1/audit` | GET | `limit`, `offset` | `List[AuditRecordResponse]` | Compliance DB |

---

## 5. Model Context Protocol (MCP) Architecture (Member 1)

The MCP Server implements the standard protocol for AI agent tool execution:

```mermaid
sequenceDiagram
    autonumber
    actor User as Operations Manager
    participant LLM as IBM Bob / Agent Copilot
    participant MCP as FastMCP Server
    participant API as FastAPI Backend
    participant DB as PostgreSQL DB

    User->>LLM: "Check temperature excursions and give me reroute recommendations for shipment S101"
    LLM->>MCP: check_cold_chain_status(shipment_id="S101")
    MCP->>API: GET /api/v1/shipments/S101/cold-chain
    API-->>MCP: {has_excursion: true, severity: "CRITICAL", max_temp: 11.4}
    MCP-->>LLM: Structured JSON Telemetry

    LLM->>MCP: simulate_what_if_route(shipment_id="S101", candidate_route_id="R14")
    MCP->>API: POST /api/v1/simulations/route
    API-->>MCP: {current_delay: 42h, simulated_delay: 6h, saved_cost: 250000}
    MCP-->>LLM: Simulation Analysis

    LLM-->>User: "Shipment S101 has critical cold-chain excursion (>11°C). Rerouting to R14 with Reefer V17 reduces delay by 36h and protects ₹1.2M vaccine cargo. [APPROVE / REJECT]?"
```

### Registered MCP Tools:
1. `get_disruption_impact(disruption_id: str)`
2. `get_shipment_risk(shipment_id: str)`
3. `check_cold_chain_status(shipment_id: str)`
4. `get_fleet_recommendations(origin: str, destination: str, is_refrigerated: bool)`
5. `simulate_what_if_route(shipment_id: str, candidate_route_id: str)`
6. `get_recommendation_and_approve(recommendation_id: str, action: str, approver: str)`
