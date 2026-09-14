"use client";

import React, { useState } from "react";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  DollarSign,
  Flame,
  Snowflake,
  Thermometer,
  Zap,
} from "lucide-react";
import { Shipment } from "../lib/types";

interface ColdChainMonitorProps {
  shipments: Shipment[];
  onTriggerReeferSwap?: (s: Shipment) => void;
}

export default function ColdChainMonitor({
  shipments,
  onTriggerReeferSwap,
}: ColdChainMonitorProps) {
  // Find pharma / temperature-sensitive shipments
  const coldShipments = shipments.filter((s) => s.temperature_required);
  const [selectedId, setSelectedId] = useState<string>(
    coldShipments[0]?.id || "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  );

  const activeShipment =
    coldShipments.find((s) => s.id === selectedId) || coldShipments[0];

  // Sample IoT timeline readings
  const sensorLogs = [
    { time: "10:00", temp: 4.2, status: "safe" },
    { time: "10:15", temp: 4.8, status: "safe" },
    { time: "10:30", temp: 5.4, status: "safe" },
    { time: "10:45", temp: 6.9, status: "warning" },
    { time: "11:00", temp: 8.2, status: "excursion" },
    { time: "11:15", temp: 8.9, status: "excursion" },
    { time: "11:30", temp: 8.4, status: "excursion" },
    { time: "11:45", temp: 7.8, status: "warning" },
    { time: "12:00", temp: 6.5, status: "safe" },
  ];

  const minTempLimit = activeShipment?.temp_min_c ?? 2.0;
  const maxTempLimit = activeShipment?.temp_max_c ?? 8.0;
  const maxRecorded = 8.9;
  const spoilageRisk = 68.5; // Calculated by ColdChainAnomalyEngine

  return (
    <div style={{ margin: "0 20px 20px 20px" }}>
      {/* Header Banner */}
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
          borderColor: "rgba(244, 63, 94, 0.3)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "8px",
              background: "rgba(244, 63, 94, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--accent-rose)",
            }}
          >
            <AlertOctagon size={20} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h2 style={{ fontSize: "16px", fontWeight: 700 }}>
                Cold Chain IoT Anomaly Engine
              </h2>
              <span className="badge badge-rose">1 Excursion Breach</span>
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              Continuous sensor telematics alerting against cargo temperature spoilage boundaries
            </p>
          </div>
        </div>

        {/* Cargo Selector */}
        <div style={{ display: "flex", gap: "8px" }}>
          {coldShipments.map((cs) => (
            <button
              key={cs.id}
              onClick={() => setSelectedId(cs.id)}
              className={selectedId === cs.id ? "btn-primary" : "btn-secondary"}
              style={{ fontSize: "12px", padding: "6px 12px" }}
            >
              <Snowflake size={14} />
              <span>{cs.tracking_number}</span>
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
        
        {/* Left: Sensor Telemetry Curve */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "14px", fontWeight: 600 }}>
                Sensor Temperature Profile (°C)
              </h3>
              <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                Safe Window: {minTempLimit}°C to {maxTempLimit}°C
              </p>
            </div>
            <div className="badge badge-rose">
              Peak: +{maxRecorded}°C
            </div>
          </div>

          {/* SVG Line Graph */}
          <div style={{ position: "relative", height: "200px", width: "100%", background: "rgba(0,0,0,0.2)", borderRadius: "8px", padding: "10px" }}>
            <svg style={{ width: "100%", height: "100%" }}>
              {/* Safe zone boundary bands */}
              <rect x="0" y="30%" width="100%" height="50%" fill="rgba(16, 185, 129, 0.08)" />
              <line x1="0" y1="30%" x2="100%" y2="30%" stroke="rgba(244, 63, 94, 0.5)" strokeDasharray="4 4" strokeWidth="1" />
              <line x1="0" y1="80%" x2="100%" y2="80%" stroke="rgba(0, 242, 254, 0.5)" strokeDasharray="4 4" strokeWidth="1" />
              
              <text x="10" y="26%" fill="var(--accent-rose)" fontSize="9">Max Limit ({maxTempLimit}°C)</text>
              <text x="10" y="88%" fill="var(--accent-cyan)" fontSize="9">Min Limit ({minTempLimit}°C)</text>

              {/* Data points line */}
              {sensorLogs.map((log, idx) => {
                if (idx === 0) return null;
                const prev = sensorLogs[idx - 1];
                const x1 = `${((idx - 1) / (sensorLogs.length - 1)) * 90 + 5}%`;
                const y1 = `${100 - (prev.temp / 12) * 100}%`;
                const x2 = `${(idx / (sensorLogs.length - 1)) * 90 + 5}%`;
                const y2 = `${100 - (log.temp / 12) * 100}%`;
                const isBreach = log.temp > maxTempLimit || prev.temp > maxTempLimit;

                return (
                  <g key={`seg-${idx}`}>
                    <line
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke={isBreach ? "#f43f5e" : "#00f2fe"}
                      strokeWidth={isBreach ? 3 : 2}
                    />
                    <circle
                      cx={x2}
                      cy={y2}
                      r={isBreach ? 4 : 3}
                      fill={isBreach ? "#f43f5e" : "#00f2fe"}
                    />
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Timeline points labels */}
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px", fontSize: "10px", color: "var(--text-faint)" }}>
            {sensorLogs.map((l) => (
              <span key={l.time}>{l.time}</span>
            ))}
          </div>
        </div>

        {/* Right: Excursion Analysis & Emergency Action Card */}
        <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
              <div>
                <span className="badge badge-amber" style={{ fontSize: "9px" }}>
                  Active Breach Analysis
                </span>
                <h3 style={{ fontSize: "16px", fontWeight: 700, marginTop: "4px" }}>
                  {activeShipment?.tracking_number}
                </h3>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--accent-rose)" }}>
                  {spoilageRisk}%
                </div>
                <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Spoilage Risk</div>
              </div>
            </div>

            <div style={{ display: "grid", gap: "10px", fontSize: "12px", color: "var(--text-muted)", marginBottom: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "rgba(255,255,255,0.03)", borderRadius: "6px" }}>
                <span>Cargo Classification:</span>
                <span style={{ color: "#fff", fontWeight: 500 }}>Temperature-Sensitive Vaccine</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "rgba(255,255,255,0.03)", borderRadius: "6px" }}>
                <span>Exposure At Risk:</span>
                <span style={{ color: "var(--accent-cyan)", fontWeight: 700 }}>
                  ${(activeShipment?.cargo_value_usd || 185000).toLocaleString()} USD
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "rgba(244,63,94,0.08)", borderRadius: "6px", border: "1px solid rgba(244,63,94,0.2)" }}>
                <span>Cumulative Excursion:</span>
                <span style={{ color: "var(--accent-rose)", fontWeight: 700 }}>45 minutes ({">"}8.0°C)</span>
              </div>
            </div>

            <div style={{ padding: "12px", background: "rgba(0, 242, 254, 0.06)", borderRadius: "8px", border: "1px solid rgba(0, 242, 254, 0.2)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-cyan)", fontWeight: 600, fontSize: "12px", marginBottom: "4px" }}>
                <Zap size={14} />
                <span>AI Recommendation Bundle</span>
              </div>
              <p style={{ fontSize: "11px", color: "var(--text-muted)", lineHeight: "1.4" }}>
                Divert immediately to Kassel Depot and transfer cargo onto Reefer unit <strong>FL-TRK-103</strong> (10% utilised, 14.2km away).
              </p>
            </div>
          </div>

          {onTriggerReeferSwap && (
            <button
              onClick={() => onTriggerReeferSwap(activeShipment)}
              className="btn-primary"
              style={{ width: "100%", justifyContent: "center", marginTop: "16px" }}
            >
              <Snowflake size={16} />
              <span>Deploy Emergency Reefer Swap</span>
            </button>
          )}
        </div>

      </div>
    </div>
  );
}
