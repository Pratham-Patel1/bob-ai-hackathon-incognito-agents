"use client";

import React from "react";
import {
  AlertTriangle,
  Compass,
  ExternalLink,
  MapPin,
  Navigation,
  ShieldAlert,
  Snowflake,
  Truck,
  Zap,
} from "lucide-react";
import { Shipment, Disruption } from "../lib/types";
import { formatCurrency } from "../lib/api";

interface ControlTowerMapProps {
  shipments: Shipment[];
  disruptions: Disruption[];
  selectedShipment: Shipment | null;
  onSelectShipment: (s: Shipment) => void;
  onSimulateShipment?: (s: Shipment) => void;
}

export default function ControlTowerMap({
  shipments,
  disruptions,
  selectedShipment,
  onSelectShipment,
  onSimulateShipment,
}: ControlTowerMapProps) {
  // Map viewport bounds (Europe corridor: 46°N to 56°N, -2°E to 16°E)
  const MIN_LAT = 46.0;
  const MAX_LAT = 56.0;
  const MIN_LNG = -2.0;
  const MAX_LNG = 16.0;

  const toX = (lng: number) => Math.max(6, Math.min(94, ((lng - MIN_LNG) / (MAX_LNG - MIN_LNG)) * 100));
  const toY = (lat: number) => Math.max(6, Math.min(94, (1 - (lat - MIN_LAT) / (MAX_LAT - MIN_LAT)) * 100));

  const HUBS = [
    { name: "Hamburg", lat: 53.55, lng: 9.99 },
    { name: "Frankfurt", lat: 50.11, lng: 8.68 },
    { name: "Rotterdam", lat: 51.92, lng: 4.48 },
    { name: "Antwerp", lat: 51.22, lng: 4.4 },
    { name: "Berlin", lat: 52.52, lng: 13.4 },
    { name: "Munich", lat: 48.14, lng: 11.58 },
    { name: "Paris", lat: 48.86, lng: 2.35 },
    { name: "London", lat: 51.51, lng: -0.13 },
    { name: "Amsterdam", lat: 52.37, lng: 4.9 },
  ];

  return (
    <div className="glass-panel" style={{ overflow: "hidden", position: "relative" }}>
      {/* Top Bar */}
      <div
        style={{
          padding: "10px 18px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "rgba(11, 15, 25, 0.4)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Compass size={15} color="var(--accent-cyan)" />
          <span style={{ fontSize: "13px", fontWeight: 600 }}>
            Geospatial Freight Corridors & Blast-Radius Detection
          </span>
        </div>

        {/* Legend */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px", fontSize: "11px", color: "var(--text-muted)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: "var(--accent-rose)" }} />
            <span>At-Risk Lane</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: "var(--accent-emerald)" }} />
            <span>Clear Corridor</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <span
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                border: "1px dashed var(--accent-rose)",
                background: "rgba(244, 63, 94, 0.15)",
              }}
            />
            <span>Storm Zone</span>
          </div>
        </div>
      </div>

      {/* Map Canvas */}
      <div style={{ position: "relative", height: "390px", width: "100%", background: "#060913" }}>
        <svg style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}>
          <defs>
            <pattern id="grid-dots" width="30" height="30" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1" fill="rgba(255, 255, 255, 0.04)" />
            </pattern>
            <radialGradient id="storm-glow">
              <stop offset="0%" stopColor="rgba(244, 63, 94, 0.35)" />
              <stop offset="60%" stopColor="rgba(244, 63, 94, 0.12)" />
              <stop offset="100%" stopColor="rgba(244, 63, 94, 0.0)" />
            </radialGradient>
          </defs>

          <rect width="100%" height="100%" fill="url(#grid-dots)" />

          {/* Reference cities hubs */}
          {HUBS.map((c) => {
            const cx = `${toX(c.lng)}%`;
            const cy = `${toY(c.lat)}%`;
            return (
              <g key={c.name}>
                <circle cx={cx} cy={cy} r="2.5" fill="#475569" />
                <text
                  x={cx}
                  y={cy}
                  dy="-6"
                  textAnchor="middle"
                  fill="#64748b"
                  fontSize="9"
                  fontFamily="Inter"
                >
                  {c.name}
                </text>
              </g>
            );
          })}

          {/* Disruption Radius Circles */}
          {disruptions.map((d) => {
            const cx = `${toX(d.longitude)}%`;
            const cy = `${toY(d.latitude)}%`;
            const r = Math.min(100, Math.max(30, d.affected_radius_km * 0.32));
            return (
              <g key={d.id}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={r}
                  fill="url(#storm-glow)"
                  stroke="rgba(244, 63, 94, 0.5)"
                  strokeWidth="1.2"
                  strokeDasharray="3 3"
                />
                <circle cx={cx} cy={cy} r="4" fill="var(--accent-rose)" />
              </g>
            );
          })}

          {/* Route Corridors */}
          {shipments.map((s) => {
            const x1 = toX(s.origin_lng);
            const y1 = toY(s.origin_lat);
            const x2 = toX(s.destination_lng);
            const y2 = toY(s.destination_lat);
            const isAtRisk = s.status === "at_risk" || s.risk_score > 70;
            const isSelected = selectedShipment?.id === s.id;

            const mx = (x1 + x2) / 2;
            const my = (y1 + y2) / 2 - 3;

            return (
              <path
                key={`p-${s.id}`}
                d={`M ${x1}% ${y1}% Q ${mx}% ${my}% ${x2}% ${y2}%`}
                fill="none"
                stroke={isSelected ? "var(--accent-cyan)" : isAtRisk ? "var(--accent-rose)" : "var(--accent-emerald)"}
                strokeWidth={isSelected ? "2.5" : "1.8"}
                strokeDasharray={isAtRisk ? "5 3" : "none"}
                opacity={isSelected ? 1 : 0.6}
              />
            );
          })}
        </svg>

        {/* Live Shipment Marker Pins */}
        {shipments.map((s) => {
          const px = `${toX(s.current_lng)}%`;
          const py = `${toY(s.current_lat)}%`;
          const isAtRisk = s.status === "at_risk" || s.risk_score > 70;
          const isSelected = selectedShipment?.id === s.id;

          return (
            <div
              key={s.id}
              onClick={() => onSelectShipment(s)}
              style={{
                position: "absolute",
                left: px,
                top: py,
                transform: "translate(-50%, -50%)",
                cursor: "pointer",
                zIndex: isSelected ? 20 : 10,
              }}
            >
              {/* Outer Pulse Ping */}
              <div
                style={{
                  width: "16px",
                  height: "16px",
                  borderRadius: "50%",
                  background: isAtRisk ? "var(--accent-rose)" : "var(--accent-emerald)",
                  border: "2px solid #ffffff",
                  boxShadow: isAtRisk
                    ? "0 0 12px rgba(244, 63, 94, 0.9)"
                    : "0 0 10px rgba(16, 185, 129, 0.8)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <div style={{ width: "4px", height: "4px", borderRadius: "50%", background: "#fff" }} />
              </div>

              {/* Minimal Clean Tag */}
              <div
                style={{
                  position: "absolute",
                  top: "18px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  whiteSpace: "nowrap",
                  background: isSelected ? "var(--accent-cyan)" : "rgba(15, 23, 42, 0.9)",
                  color: isSelected ? "#050811" : "#ffffff",
                  padding: "1px 6px",
                  borderRadius: "4px",
                  fontSize: "9px",
                  fontWeight: 600,
                  border: isSelected ? "1px solid var(--accent-cyan)" : "1px solid rgba(255, 255, 255, 0.1)",
                }}
              >
                {s.tracking_number.split("-")[1]} • {s.risk_score}
              </div>
            </div>
          );
        })}

        {/* Selected Vehicle Float Card */}
        {selectedShipment && (
          <div
            className="glass-panel"
            style={{
              position: "absolute",
              right: "12px",
              bottom: "12px",
              width: "280px",
              padding: "12px 14px",
              zIndex: 30,
              background: "rgba(12, 18, 32, 0.95)",
              border: "1px solid var(--accent-cyan)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "#fff" }}>
                {selectedShipment.tracking_number}
              </span>
              <span
                className={`badge badge-${selectedShipment.status === "at_risk" ? "rose" : "emerald"}`}
                style={{ fontSize: "9px" }}
              >
                {selectedShipment.status.toUpperCase()}
              </span>
            </div>

            <div style={{ fontSize: "11px", color: "var(--text-muted)", display: "grid", gap: "4px", marginBottom: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Route:</span>
                <span style={{ color: "#fff" }}>{selectedShipment.origin} → {selectedShipment.destination}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Cargo:</span>
                <span style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>
                  {formatCurrency(selectedShipment.cargo_value_usd)}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Risk Level:</span>
                <span style={{ color: selectedShipment.risk_score > 70 ? "var(--accent-rose)" : "var(--accent-emerald)", fontWeight: 700 }}>
                  {selectedShipment.risk_score} / 100 ({selectedShipment.risk_level.toUpperCase()})
                </span>
              </div>
            </div>

            {onSimulateShipment && (
              <button
                onClick={() => onSimulateShipment(selectedShipment)}
                className="btn-primary"
                style={{ width: "100%", justifyContent: "center", fontSize: "11px", padding: "6px" }}
              >
                <Zap size={12} />
                <span>Simulate Bypass Corridor</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
