import {
  Shipment,
  Disruption,
  FleetVehicle,
  FleetSummary,
  Recommendation,
  DecisionAudit,
  ColdChainTelemetry,
  RouteSimulationResult,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ── Mock Fallbacks for Immediate Interactive Demo ─────────────────────────────
export const MOCK_SHIPMENTS: Shipment[] = [
  {
    id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    tracking_number: "TRK-PHARMA-2026-001",
    origin: "Hamburg",
    destination: "Frankfurt",
    origin_lat: 53.5511,
    origin_lng: 9.9937,
    destination_lat: 50.1109,
    destination_lng: 8.6821,
    current_location: "Kassel Corridor",
    current_lat: 51.3127,
    current_lng: 9.4797,
    status: "at_risk",
    scheduled_departure: new Date(Date.now() - 4 * 3600000).toISOString(),
    scheduled_arrival: new Date(Date.now() + 3 * 3600000).toISOString(),
    estimated_arrival: new Date(Date.now() + 7 * 3600000).toISOString(),
    cargo_type: "temperature_sensitive",
    cargo_value_usd: 185000,
    weight_kg: 4200,
    temperature_required: true,
    temp_min_c: 2.0,
    temp_max_c: 8.0,
    risk_score: 78.5,
    risk_level: "high",
    carrier: {
      id: "c-01",
      name: "Apex Global Freight",
      code: "APEX",
      reliability_score: 0.94,
    },
    route: {
      id: "r-01",
      code: "RT-01",
      name: "Hamburg to Frankfurt Road Express",
      distance_km: 492.0,
    },
  },
  {
    id: "4fa85f64-5717-4562-b3fc-2c963f66afa7",
    tracking_number: "TRK-AUTO-2026-042",
    origin: "Rotterdam",
    destination: "Munich",
    origin_lat: 51.9244,
    origin_lng: 4.4777,
    destination_lat: 48.1351,
    destination_lng: 11.582,
    current_location: "Rhine Hub",
    current_lat: 50.0782,
    current_lng: 8.243,
    status: "delayed",
    scheduled_departure: new Date(Date.now() - 8 * 3600000).toISOString(),
    scheduled_arrival: new Date(Date.now() + 2 * 3600000).toISOString(),
    estimated_arrival: new Date(Date.now() + 10 * 3600000).toISOString(),
    cargo_type: "automotive_parts",
    cargo_value_usd: 320000,
    weight_kg: 14500,
    temperature_required: false,
    risk_score: 64.0,
    risk_level: "medium",
    carrier: {
      id: "c-02",
      name: "TransEuropa Express",
      code: "TEX",
      reliability_score: 0.91,
    },
    route: {
      id: "r-02",
      code: "RT-02",
      name: "Rotterdam to Munich Rail Link",
      distance_km: 820.0,
    },
  },
  {
    id: "5fa85f64-5717-4562-b3fc-2c963f66afa8",
    tracking_number: "TRK-ELEC-2026-109",
    origin: "Antwerp",
    destination: "Paris",
    origin_lat: 51.2194,
    origin_lng: 4.4025,
    destination_lat: 48.8566,
    destination_lng: 2.3522,
    current_location: "Lille Gateway",
    current_lat: 50.6292,
    current_lng: 3.0573,
    status: "in_transit",
    scheduled_departure: new Date(Date.now() - 2 * 3600000).toISOString(),
    scheduled_arrival: new Date(Date.now() + 2.5 * 3600000).toISOString(),
    estimated_arrival: new Date(Date.now() + 2.5 * 3600000).toISOString(),
    cargo_type: "electronics",
    cargo_value_usd: 450000,
    weight_kg: 3200,
    temperature_required: false,
    risk_score: 18.2,
    risk_level: "low",
    carrier: {
      id: "c-01",
      name: "Apex Global Freight",
      code: "APEX",
      reliability_score: 0.94,
    },
    route: {
      id: "r-03",
      code: "RT-03",
      name: "Antwerp to Paris Highway Corridor",
      distance_km: 345.0,
    },
  },
  {
    id: "6fa85f64-5717-4562-b3fc-2c963f66afa9",
    tracking_number: "TRK-BIO-2026-773",
    origin: "London",
    destination: "Amsterdam",
    origin_lat: 51.5074,
    origin_lng: -0.1278,
    destination_lat: 52.3676,
    destination_lng: 4.9041,
    current_location: "Heathrow Cargo",
    current_lat: 51.47,
    current_lng: -0.4543,
    status: "in_transit",
    scheduled_departure: new Date().toISOString(),
    scheduled_arrival: new Date(Date.now() + 3 * 3600000).toISOString(),
    estimated_arrival: new Date(Date.now() + 3 * 3600000).toISOString(),
    cargo_type: "biomedical_vaccines",
    cargo_value_usd: 890000,
    weight_kg: 850,
    temperature_required: true,
    temp_min_c: -20.0,
    temp_max_c: -10.0,
    risk_score: 22.0,
    risk_level: "low",
    carrier: {
      id: "c-04",
      name: "AeroWings Cargo",
      code: "AWC",
      reliability_score: 0.97,
    },
    route: {
      id: "r-05",
      code: "RT-05",
      name: "London to Amsterdam Air Shuttle",
      distance_km: 360.0,
    },
  },
];

export const MOCK_DISRUPTIONS: Disruption[] = [
  {
    id: "d-01",
    title: "North Sea Winter Gale Alert",
    type: "severe_weather",
    severity: "critical",
    latitude: 54.0,
    longitude: 9.5,
    affected_radius_km: 250.0,
    status: "active",
    description: "Hurricane-force gusts and storm surge halting North Sea feeder vessels and northern freight lanes.",
    estimated_delay_hours: 14.0,
    reported_at: new Date(Date.now() - 3 * 3600000).toISOString(),
  },
  {
    id: "d-02",
    title: "Frankfurt Rail Hub Signal Failure",
    type: "infrastructure",
    severity: "high",
    latitude: 50.1109,
    longitude: 8.6821,
    affected_radius_km: 60.0,
    status: "active",
    description: "Signaling hardware malfunction halting south-bound rail freight corridors across the Rhine valley.",
    estimated_delay_hours: 8.0,
    reported_at: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: "d-03",
    title: "Shanghai Port Typhoon Diversion",
    type: "cyclone",
    severity: "high",
    latitude: 31.2304,
    longitude: 121.4737,
    affected_radius_km: 180.0,
    status: "active",
    description: "Typhoon outer bands forcing vessel holding outside Yangshan deep-water container terminal.",
    estimated_delay_hours: 24.0,
    reported_at: new Date(Date.now() - 12 * 3600000).toISOString(),
  },
];

export const MOCK_FLEET: FleetVehicle[] = [
  {
    id: "fl-01",
    vehicle_code: "FL-TRK-101",
    vehicle_type: "truck",
    capacity_tons: 24.0,
    current_load_tons: 18.0,
    utilisation_percent: 75.0,
    is_refrigerated: false,
    status: "in_transit",
    latitude: 53.2,
    longitude: 9.8,
  },
  {
    id: "fl-02",
    vehicle_code: "FL-TRK-102",
    vehicle_type: "reefer_truck",
    capacity_tons: 20.0,
    current_load_tons: 15.0,
    utilisation_percent: 75.0,
    is_refrigerated: true,
    status: "in_transit",
    latitude: 50.8,
    longitude: 8.2,
  },
  {
    id: "fl-03",
    vehicle_code: "FL-TRK-103",
    vehicle_type: "reefer_truck",
    capacity_tons: 20.0,
    current_load_tons: 2.0,
    utilisation_percent: 10.0,
    is_refrigerated: true,
    status: "available",
    latitude: 50.11,
    longitude: 8.68,
    distance_km: 14.2,
    suitability_score: 94.0,
  },
  {
    id: "fl-04",
    vehicle_code: "FL-TRK-104",
    vehicle_type: "truck",
    capacity_tons: 24.0,
    current_load_tons: 3.0,
    utilisation_percent: 12.5,
    is_refrigerated: false,
    status: "available",
    latitude: 53.55,
    longitude: 9.99,
  },
  {
    id: "fl-05",
    vehicle_code: "FL-VAN-201",
    vehicle_type: "van",
    capacity_tons: 3.5,
    current_load_tons: 0.5,
    utilisation_percent: 14.3,
    is_refrigerated: true,
    status: "idle",
    latitude: 51.92,
    longitude: 4.47,
  },
  {
    id: "fl-06",
    vehicle_code: "FL-TRK-105",
    vehicle_type: "truck",
    capacity_tons: 26.0,
    current_load_tons: 25.5,
    utilisation_percent: 98.1,
    is_refrigerated: false,
    status: "in_transit",
    latitude: 48.85,
    longitude: 2.35,
  },
];

export const MOCK_RECOMMENDATIONS: Recommendation[] = [
  {
    id: "rec-01",
    shipment_id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    disruption_id: "d-01",
    type: "reroute",
    priority: "critical",
    title: "Reroute — TRK-PHARMA-2026-001 via Southern Autobahn",
    description: "North Sea winter storm blocking coastal lanes. Divert through inland corridor and dispatch Reefer FL-TRK-103 to prevent vaccine spoilage.",
    reason: "Severe temperature spike detected (8.9°C > 8.0°C limit) coupled with 14hr coastal storm delay.",
    reasoning_factors: [
      "Avoids 250km blast-radius storm zone",
      "Saves $185,000 perishable cargo from spoilage",
      "Reduces predicted transit delay by 9.5 hours",
      "Pre-selected high-reliability carrier (Apex 94%)"
    ],
    estimated_savings_usd: 185000,
    estimated_delay_reduction_hours: 9.5,
    requires_approval: true,
    status: "pending",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "rec-02",
    shipment_id: "4fa85f64-5717-4562-b3fc-2c963f66afa7",
    disruption_id: "d-02",
    type: "carrier_swap",
    priority: "high",
    title: "Carrier Swap — TRK-AUTO-2026-042 to Rhine-Alpine Roadway",
    description: "Frankfurt rail signaling failure causing 8h cascade backlog. Transfer container onto Vanguard road carrier.",
    reason: "Signal failure corridor blockage creates high risk of assembly line stoppage penalty ($45,000).",
    reasoning_factors: [
      "Avoids 8h rail queue at Frankfurt yard",
      "Prevents OEM plant shutdown penalties",
      "Roadway slot confirmed with Vanguard Roadways"
    ],
    estimated_savings_usd: 45000,
    estimated_delay_reduction_hours: 6.0,
    requires_approval: true,
    status: "pending",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

export const MOCK_AUDIT_LOGS: DecisionAudit[] = [
  {
    id: "aud-01",
    entity_type: "recommendation",
    entity_id: "rec-00-seed",
    action: "rec_approved",
    actor: "IBM Bob Copilot",
    actor_type: "ai_agent",
    reasoning: "Approved alternative route RT-01 avoiding gale storm based on digital twin simulation.",
    previous_state: { status: "pending" },
    new_state: { status: "approved", approved_by: "IBM Bob Copilot" },
    timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
  },
  {
    id: "aud-02",
    entity_type: "shipment",
    entity_id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    action: "risk_escalation",
    actor: "ShipmentRiskEngine",
    actor_type: "system",
    reasoning: "Risk score escalated from 45.0 to 78.5 due to storm proximity and cold chain deviation.",
    previous_state: { risk_level: "medium", risk_score: 45.0 },
    new_state: { risk_level: "high", risk_score: 78.5 },
    timestamp: new Date(Date.now() - 90 * 60000).toISOString(),
  },
];

// ── Real API Caller with Fallback ─────────────────────────────────────────────
async function safeFetch<T>(endpoint: string, fallback: T): Promise<{ data: T; isLive: boolean }> {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return { data, isLive: true };
  } catch (err) {
    return { data: fallback, isLive: false };
  }
}

export async function getShipments(): Promise<{ shipments: Shipment[]; isLive: boolean }> {
  const { data, isLive } = await safeFetch<Shipment[]>("/shipments", MOCK_SHIPMENTS);
  return { shipments: data, isLive };
}

export async function getDisruptions(): Promise<{ disruptions: Disruption[]; isLive: boolean }> {
  const { data, isLive } = await safeFetch<Disruption[]>("/disruptions", MOCK_DISRUPTIONS);
  return { disruptions: data, isLive };
}

export async function getFleet(): Promise<{ fleet: FleetVehicle[]; isLive: boolean }> {
  const { data, isLive } = await safeFetch<FleetVehicle[]>("/fleet", MOCK_FLEET);
  return { fleet: data, isLive };
}

export async function getFleetIntelligence(): Promise<{
  summary: FleetSummary;
  redeployment_candidates: FleetVehicle[];
  isLive: boolean;
}> {
  const defaultSummary: FleetSummary = {
    total_vehicles: 6,
    idle_count: 1,
    available_count: 2,
    overloaded_count: 1,
    in_transit_count: 2,
    maintenance_count: 0,
    average_utilisation_percent: 47.5,
    refrigerated_available: 2,
  };
  const { data, isLive } = await safeFetch<any>("/fleet/intelligence", {
    summary: defaultSummary,
    redeployment_candidates: MOCK_FLEET.filter((f) => f.status === "available"),
  });
  return {
    summary: data.summary || defaultSummary,
    redeployment_candidates: data.redeployment_candidates || [],
    isLive,
  };
}

export async function getRecommendations(): Promise<{ recommendations: Recommendation[]; isLive: boolean }> {
  const { data, isLive } = await safeFetch<Recommendation[]>("/recommendations", MOCK_RECOMMENDATIONS);
  return { recommendations: data, isLive };
}

export async function approveRecommendationApi(
  id: string,
  actor: string,
  notes: string
): Promise<{ success: boolean; data?: any }> {
  try {
    const res = await fetch(`${API_BASE}/recommendations/${id}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor, notes }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return { success: true, data };
  } catch (err) {
    // Offline simulation update
    return { success: true, data: { status: "approved", approved_by: actor } };
  }
}

export async function rejectRecommendationApi(
  id: string,
  actor: string,
  notes: string
): Promise<{ success: boolean; data?: any }> {
  try {
    const res = await fetch(`${API_BASE}/recommendations/${id}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor, notes }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return { success: true, data };
  } catch (err) {
    return { success: true, data: { status: "rejected", approved_by: actor } };
  }
}

export async function simulateRouteApi(payload: {
  shipment_id: string;
  candidate_route_id: string;
  candidate_carrier_id: string;
}): Promise<RouteSimulationResult> {
  const fallback: RouteSimulationResult = {
    shipment_id: payload.shipment_id,
    baseline: {
      total_delay_hours: 32.5,
      total_cost_usd: 12400,
      risk_score: 82.0,
    },
    simulated: {
      total_delay_hours: 6.0,
      total_cost_usd: 14100,
      risk_score: 21.5,
    },
    delta: {
      delay_reduction_hours: 26.5,
      cost_variance_usd: 1700,
      risk_reduction_score: 60.5,
    },
    business_impact: {
      roi_factor: 5.2,
      spoiled_cargo_prevented_usd: 185000,
    },
  };

  try {
    const res = await fetch(`${API_BASE}/simulations/route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error();
    return await res.json();
  } catch {
    return fallback;
  }
}

export async function getAuditLogs(): Promise<{ logs: DecisionAudit[]; isLive: boolean }> {
  const { data, isLive } = await safeFetch<DecisionAudit[]>("/audit?limit=50", MOCK_AUDIT_LOGS);
  return { logs: data, isLive };
}
