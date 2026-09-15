"use client";

import React, { useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import { Shipment, RouteSimulationResult } from "../lib/types";
import { simulateRouteApi } from "../lib/api";

interface SimulationStudioProps {
  shipments: Shipment[];
  onCommitSimulation?: (sim: RouteSimulationResult) => void;
}

export default function SimulationStudio({
  shipments,
  onCommitSimulation,
}: SimulationStudioProps) {
  const [selectedShipmentId, setSelectedShipmentId] = useState<string>(
    shipments[0]?.id || "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  );
  const [selectedRoute, setSelectedRoute] = useState<string>("RT-01");
  const [selectedCarrier, setSelectedCarrier] = useState<string>("APEX");
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<RouteSimulationResult | null>({
    shipment_id: selectedShipmentId,
    baseline: {
      total_delay_hours: 36.0,
      total_cost_usd: 12500,
      risk_score: 82.0,
    },
    simulated: {
      total_delay_hours: 6.5,
      total_cost_usd: 14200,
      risk_score: 24.0,
    },
    delta: {
      delay_reduction_hours: 29.5,
      cost_variance_usd: 1700,
      risk_reduction_score: 58.0,
    },
    business_impact: {
      roi_factor: 4.2,
      spoiled_cargo_prevented_usd: 185000,
    },
  });

  const activeShipment = shipments.find((s) => s.id === selectedShipmentId) || shipments[0];

  const handleRunSimulation = async () => {
    setIsSimulating(true);
    const res = await simulateRouteApi({
      shipment_id: selectedShipmentId,
      candidate_route_id: selectedRoute,
      candidate_carrier_id: selectedCarrier,
    });
    setSimulationResult(res);
    setIsSimulating(false);
  };

  return (
    <div style={{ margin: "0 20px 20px 20px" }}>
      {/* Studio Header */}
      <div
        className="glass-panel"
        style={{
          padding: "16px 20px",
          marginBottom: "16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "8px",
              background: "rgba(0, 242, 254, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--accent-cyan)",
            }}
          >
            <Cpu size={20} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h2 style={{ fontSize: "16px", fontWeight: 700 }}>
                Digital Twin "What-If" Simulation Studio
              </h2>
              <span className="badge badge-cyan">In-Memory Engine</span>
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              Test multi-modal route & carrier alternatives without impacting live production state
            </p>
          </div>
        </div>

        {/* Action button */}
        <button
          onClick={handleRunSimulation}
          disabled={isSimulating}
          className="btn-primary"
        >
          <Play size={16} fill="#040d21" />
          <span>{isSimulating ? "Simulating Corridors..." : "Execute Simulation"}</span>
        </button>
      </div>

      {/* Configuration Bar */}
      <div
        className="glass-panel"
        style={{
          padding: "16px 20px",
          marginBottom: "16px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "16px",
        }}
      >
        <div>
          <label style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
            Target In-Transit Cargo:
          </label>
          <select
            value={selectedShipmentId}
            onChange={(e) => setSelectedShipmentId(e.target.value)}
            style={{
              width: "100%",
              padding: "9px 12px",
              borderRadius: "8px",
              background: "rgba(15, 23, 42, 0.8)",
              border: "1px solid var(--border-subtle)",
              color: "#fff",
              fontSize: "13px",
              outline: "none",
            }}
          >
            {shipments.map((s) => (
              <option key={s.id} value={s.id}>
                {s.tracking_number} ({s.origin} → {s.destination})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
            Candidate Alternative Route:
          </label>
          <select
            value={selectedRoute}
            onChange={(e) => setSelectedRoute(e.target.value)}
            style={{
              width: "100%",
              padding: "9px 12px",
              borderRadius: "8px",
              background: "rgba(15, 23, 42, 0.8)",
              border: "1px solid var(--border-subtle)",
              color: "#fff",
              fontSize: "13px",
              outline: "none",
            }}
          >
            <option value="RT-01">RT-01: Southern Autobahn Express (Road, 492km)</option>
            <option value="RT-02">RT-02: Rhine Inland Rail Bypass (Rail, 820km)</option>
            <option value="RT-09">RT-09: Frankfurt-Berlin Highway (Road, 550km)</option>
            <option value="RT-26">RT-26: Northern Intermodal Link (Multimodal, 290km)</option>
          </select>
        </div>

        <div>
          <label style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
            Candidate Carrier:
          </label>
          <select
            value={selectedCarrier}
            onChange={(e) => setSelectedCarrier(e.target.value)}
            style={{
              width: "100%",
              padding: "9px 12px",
              borderRadius: "8px",
              background: "rgba(15, 23, 42, 0.8)",
              border: "1px solid var(--border-subtle)",
              color: "#fff",
              fontSize: "13px",
              outline: "none",
            }}
          >
            <option value="APEX">Apex Global Freight (Reliability: 94%, Cost: 1.1x)</option>
            <option value="VGR">Vanguard Roadways (Reliability: 87%, Cost: 1.0x)</option>
            <option value="TEX">TransEuropa Express Rail (Reliability: 91%, Cost: 0.95x)</option>
            <option value="RAR">Rhine-Alpine Railways (Reliability: 93%, Cost: 0.90x)</option>
          </select>
        </div>
      </div>

      {/* Side-by-Side Comparison Workspace */}
      {simulationResult && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
          
          {/* Baseline Plan */}
          <div className="glass-panel" style={{ padding: "20px", border: "1px solid rgba(244, 63, 94, 0.3)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <div>
                <span className="badge badge-rose" style={{ fontSize: "9px" }}>Current Disrupted State</span>
                <h3 style={{ fontSize: "16px", fontWeight: 700, marginTop: "4px" }}>Baseline Trajectory</h3>
              </div>
              <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "rgba(244, 63, 94, 0.15)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent-rose)" }}>
                <Clock size={16} />
              </div>
            </div>

            <div style={{ display: "grid", gap: "12px", fontSize: "13px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", background: "rgba(0,0,0,0.2)", borderRadius: "6px" }}>
                <span style={{ color: "var(--text-muted)" }}>Estimated Delay:</span>
                <span style={{ color: "var(--accent-rose)", fontWeight: 700 }}>
                  +{simulationResult.baseline.total_delay_hours.toFixed(1)} Hours
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", background: "rgba(0,0,0,0.2)", borderRadius: "6px" }}>
                <span style={{ color: "var(--text-muted)" }}>Total Logistics Cost:</span>
                <span style={{ color: "#fff", fontWeight: 600 }}>
                  ${simulationResult.baseline.total_cost_usd.toLocaleString()}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", background: "rgba(0,0,0,0.2)", borderRadius: "6px" }}>
                <span style={{ color: "var(--text-muted)" }}>Risk Score:</span>
                <span style={{ color: "var(--accent-rose)", fontWeight: 700 }}>
                  {simulationResult.baseline.risk_score} / 100 (CRITICAL)
                </span>
              </div>
            </div>
          </div>

          {/* Simulated Alternative Plan */}
          <div className="glass-panel" style={{ padding: "20px", border: "1px solid rgba(16, 185, 129, 0.4)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <div>
                <span className="badge badge-emerald" style={{ fontSize: "9px" }}>Simulated Corridor</span>
                <h3 style={{ fontSize: "16px", fontWeight: 700, marginTop: "4px" }}>Alternative Outcome</h3>
              </div>
              <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "rgba(16, 185, 129, 0.15)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent-emerald)" }}>
                <Sparkles size={16} />
              </div>
            </div>

            <div style={{ display: "grid", gap: "12px", fontSize: "13px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", background: "rgba(0,0,0,0.2)", borderRadius: "6px" }}>
                <span style={{ color: "var(--text-muted)" }}>Simulated Delay:</span>
                <span style={{ color: "var(--accent-emerald)", fontWeight: 700 }}>
                  +{simulationResult.simulated.total_delay_hours.toFixed(1)} Hours
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", background: "rgba(0,0,0,0.2)", borderRadius: "6px" }}>
                <span style={{ color: "var(--text-muted)" }}>Simulated Cost:</span>
                <span style={{ color: "#fff", fontWeight: 600 }}>
                  ${simulationResult.simulated.total_cost_usd.toLocaleString()}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", background: "rgba(0,0,0,0.2)", borderRadius: "6px" }}>
                <span style={{ color: "var(--text-muted)" }}>Simulated Risk:</span>
                <span style={{ color: "var(--accent-emerald)", fontWeight: 700 }}>
                  {simulationResult.simulated.risk_score} / 100 (LOW)
                </span>
              </div>
            </div>
          </div>

          {/* Delta & Business Impact */}
          <div className="glass-panel" style={{ padding: "20px", background: "rgba(0, 242, 254, 0.04)", border: "1px solid rgba(0, 242, 254, 0.3)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <div>
                <span className="badge badge-cyan" style={{ fontSize: "9px" }}>Strategic Delta</span>
                <h3 style={{ fontSize: "16px", fontWeight: 700, marginTop: "4px" }}>Business Impact</h3>
              </div>
              <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "rgba(0, 242, 254, 0.15)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent-cyan)" }}>
                <TrendingDown size={16} />
              </div>
            </div>

            <div style={{ display: "grid", gap: "10px", fontSize: "12px", marginBottom: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "rgba(0,0,0,0.25)", borderRadius: "6px" }}>
                <span>Delay Reduction:</span>
                <span style={{ color: "var(--accent-emerald)", fontWeight: 700 }}>
                  -{simulationResult.delta.delay_reduction_hours.toFixed(1)} Hours
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "rgba(0,0,0,0.25)", borderRadius: "6px" }}>
                <span>Risk Reduction:</span>
                <span style={{ color: "var(--accent-cyan)", fontWeight: 700 }}>
                  -{simulationResult.delta.risk_reduction_score} pts
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "rgba(0,0,0,0.25)", borderRadius: "6px" }}>
                <span>Spoilage Prevented:</span>
                <span style={{ color: "var(--accent-emerald)", fontWeight: 700 }}>
                  ${simulationResult.business_impact.spoiled_cargo_prevented_usd.toLocaleString()}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "rgba(0,0,0,0.25)", borderRadius: "6px" }}>
                <span>ROI Multiple:</span>
                <span style={{ color: "var(--accent-cyan)", fontWeight: 800 }}>
                  {simulationResult.business_impact.roi_factor}x Cost-to-Save
                </span>
              </div>
            </div>

            {onCommitSimulation && (
              <button
                onClick={() => onCommitSimulation(simulationResult)}
                className="btn-primary"
                style={{ width: "100%", justifyContent: "center" }}
              >
                <CheckCircle2 size={16} />
                <span>Adopt Simulated Corridor</span>
              </button>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
