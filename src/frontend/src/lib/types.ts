export interface Shipment {
  id: string;
  tracking_number: string;
  origin: string;
  destination: string;
  origin_lat: number;
  origin_lng: number;
  destination_lat: number;
  destination_lng: number;
  current_location: string;
  current_lat: number;
  current_lng: number;
  carrier_id?: string;
  route_id?: string;
  fleet_id?: string;
  status: "in_transit" | "delayed" | "at_risk" | "delivered" | "exception";
  scheduled_departure: string;
  scheduled_arrival: string;
  estimated_arrival: string;
  actual_arrival?: string | null;
  cargo_type: string;
  cargo_value_usd: number;
  weight_kg: number;
  temperature_required: boolean;
  temp_min_c?: number;
  temp_max_c?: number;
  risk_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
  carrier?: {
    id: string;
    name: string;
    code: string;
    reliability_score: number;
  };
  route?: {
    id: string;
    code: string;
    name: string;
    distance_km: number;
  };
}

export interface Disruption {
  id: string;
  title: string;
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  latitude: number;
  longitude: number;
  affected_radius_km: number;
  status: "active" | "pending" | "resolved";
  description?: string;
  estimated_delay_hours: number;
  reported_at: string;
}

export interface FleetVehicle {
  id: string;
  vehicle_code: string;
  vehicle_type: string;
  capacity_tons: number;
  current_load_tons: number;
  utilisation_percent?: number;
  is_refrigerated: boolean;
  status: "available" | "idle" | "in_transit" | "maintenance";
  latitude: number;
  longitude: number;
  distance_km?: number;
  suitability_score?: number;
}

export interface FleetSummary {
  total_vehicles: number;
  idle_count: number;
  available_count: number;
  overloaded_count: number;
  in_transit_count: number;
  maintenance_count: number;
  average_utilisation_percent: number;
  refrigerated_available: number;
}

export type ReasoningFactor =
  | string
  | {
      factor?: string;
      name?: string;
      value?: number | string;
      contribution?: number;
      weight?: number;
    };

export interface Recommendation {
  id: string;
  shipment_id?: string;
  disruption_id?: string;
  type: string;
  priority: "low" | "medium" | "high" | "critical";
  title: string;
  description?: string;
  reason: string;
  reasoning_factors?: ReasoningFactor[];
  alternative_route_id?: string;
  alternative_carrier_id?: string;
  estimated_savings_usd?: number;
  estimated_delay_reduction_hours?: number;
  requires_approval: boolean;
  status: "pending" | "approved" | "rejected";
  approved_by?: string | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DecisionAudit {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  actor_type: string;
  reasoning?: string;
  previous_state?: Record<string, any>;
  new_state?: Record<string, any>;
  timestamp: string;
}

export interface ColdChainTelemetry {
  shipment_id: string;
  has_excursion: boolean;
  excursion_severity: "NONE" | "MINOR" | "MAJOR" | "CRITICAL";
  max_temp_reached: number;
  min_temp_reached: number;
  excursion_duration_mins: number;
  spoilage_risk_percent: number;
  excursions: Array<{
    start_time: string;
    end_time: string;
    duration_mins: number;
    max_deviation_c: number;
    severity: string;
    reading_count: number;
  }>;
  factors: string[];
}

export interface RouteSimulationResult {
  shipment_id: string;
  baseline: {
    total_delay_hours: number;
    total_cost_usd: number;
    risk_score: number;
  };
  simulated: {
    total_delay_hours: number;
    total_cost_usd: number;
    risk_score: number;
  };
  delta: {
    delay_reduction_hours: number;
    cost_variance_usd: number;
    risk_reduction_score: number;
  };
  business_impact: {
    roi_factor: number;
    spoiled_cargo_prevented_usd: number;
  };
}
