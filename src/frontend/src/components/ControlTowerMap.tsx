"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Compass,
  ExternalLink,
  MapPin,
  Maximize2,
  Navigation,
  ShieldAlert,
  Thermometer,
  Truck,
  Zap,
} from "lucide-react";
import { Shipment, Disruption } from "../lib/types";

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
  // Map viewport bounds (focused on Europe corridor approx: 45°N to 57°N, -5°E to 18°E)
  const MIN_LAT = 45.0;
  const MAX_LAT = 57.0;
  const MIN_LNG = -5.0;
  const MAX_LNG = 18.0;

  // Convert lat/lng to SVG coordinate percentage (0-100%)
  const toX = (lng: number) => Math.max(5, Math.min(95, ((lng - MIN_LNG) / (MAX_LNG - MIN_LNG)) * 100));
  const toY = (lat: number) => Math.max(5, Math.min(95, (1 - (lat - MIN_LAT) / (MAX_LAT - MIN_LAT)) * 100));

  // Cities anchor points for visual reference
  const REFERENCE_CITIES = [
    { name: "Hamburg", lat: 53.55, lng: 9.99 },
    { name: "Frankfurt", lat: 50.11, lng: 8.68 },
    { name: "Rotterdam", lat: 51.92, lng: 4.48 },
    { name: "Antwerp", lat: 51.22, lng: 4.4 },
    { name: "Berlin", lat: 52.52, lng: 13.4 },
    { name: "Munich", lat: 48.14, lng: 11.58 },
    { name: "Paris", lat: 48.86, lng: 2.35 },
    { name: "London", lat: 51.51, lng: -0.13 },
    { name: "Amsterdam", lat: 52.37, lng: 4.9 },
    { name: "Milan", lat: 45.46, lng: 9.19 },
  ];

  return (
    <div className="glass-panel" style={{ margin: "0 20px 20px 20px", overflow: "hidden", position: "relative" }}>
      {/* Map Header Toolbar */}
      <div
        style={{
          padding: "14px 20px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
          background: "rgba(11, 15, 25, 0.4)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Compass size={18} color="var(--accent-cyan)" />
          <h2 style={{ fontSize: "15px", fontWeight: 600 }}>
            Geospatial Digital Twin & Disruption Corridor
          </h2>
          <span className="badge badge-cyan" style={{ fontSize: "10px" }}>
            Live Telemetry • Multi-Modal
          </span>
        </div>

        {/* Legend */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px", fontSize: "11px", color: "var(--text-muted)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--accent-rose)" }} />
            <span>At Risk Cargo</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--accent-emerald)" }} />
            <span>On Schedule</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                border: "1px dashed var(--accent-rose)",
                background: "rgba(244, 63, 94, 0.2)",
              }}
            />
            <span>Blast Radius Zone</span>
          </div>
        </div>
      </div>

      {/* Main Map Canvas Area */}
      <div style={{ position: "relative", height: "480px", width: "100%", background: "#050811" }}>
        {/* Subtle coordinate grid lines */}
        <svg
          style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none" }}
        >
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.025)" strokeWidth="1" />
            </pattern>
            <radialGradient id="storm-gradient">
              <stop offset="0%" stopColor="rgba(244, 63, 94, 0.45)" />
              <stop offset="70%" stopColor="rgba(244, 63, 94, 0.15)" />
              <stop offset="100%" stopColor="rgba(244, 63, 94, 0.0)" />
            </radialGradient>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Reference cities hubs */}
          {REFERENCE_CITIES.map((c) => {
            const cx = `${toX(c.lng)}%`;
            const cy = `${toY(c.lat)}%`;
            return (
              <g key={c.name}>
                <circle cx={cx} cy={cy} r="3" fill="#334155" />
                <text
                  x={cx}
                  y={cy}
                  dy="-8"
                  textAnchor="middle"
                  fill="#64748b"
                  fontSize="10"
                  fontFamily="Inter"
                  fontWeight="500"
                >
                  {c.name}
                </text>
              </g>
            );
          })}

          {/* Disruption Blast Radius Circles */}
          {disruptions.map((d) => {
            const cx = `${toX(d.longitude)}%`;
            const cy = `${toY(d.latitude)}%`;
            const r = Math.min(120, Math.max(35, d.affected_radius_km * 0.4));
            return (
              <g key={d.id}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={r}
                  fill="url(#storm-gradient)"
                  stroke="rgba(244, 63, 94, 0.6)"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                <circle cx={cx} cy={cy} r="5" fill="var(--accent-rose)" />
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

            // Control curve mid point
            const mx = (x1 + x2) / 2;
            const my = (y1 + y2) / 2 - 4;

            return (
              <g key={`path-${s.id}`}>
                <path
                  d={`M ${x1}% ${y1}% Q ${mx}% ${my}% ${x2}% ${y2}%`}
                  fill="none"
                  stroke={isSelected ? "#00f2fe" : isAtRisk ? "#f43f5e" : "#10b981"}
                  strokeWidth={isSelected ? "3" : "2"}
                  strokeDasharray={isAtRisk ? "6 4" : "none"}
                  opacity={isSelected ? 1 : 0.65}
                />
              </g>
            );
          })}
        </svg>

        {/* Interactive Shipment Markers */}
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
              {/* Pulsating Ping */}
              <div
                style={{
                  width: "18px",
                  height: "18px",
                  borderRadius: "50%",
                  background: isAtRisk ? "var(--accent-rose)" : "var(--accent-emerald)",
                  border: "2px solid #ffffff",
                  boxShadow: isAtRisk
                    ? "0 0 16px rgba(244, 63, 94, 0.9)"
                    : "0 0 12px rgba(16, 185, 129, 0.8)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "transform 0.2s ease",
                }}
              >
                <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#fff" }} />
              </div>

              {/* Tag Label */}
              <div
                style={{
                  position: "absolute",
                  top: "22px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  whiteSpace: "nowrap",
                  background: isSelected ? "rgba(0, 242, 254, 0.9)" : "rgba(15, 23, 42, 0.85)",
                  color: isSelected ? "#050811" : "#ffffff",
                  padding: "2px 8px",
                  borderRadius: "6px",
                  fontSize: "10px",
                  fontWeight: 600,
                  border: isSelected ? "1px solid #00f2fe" : "1px solid rgba(255, 255, 255, 0.15)",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
                }}
              >
                {s.tracking_number.split("-")[1] || s.tracking_number} • {s.risk_score}
              </div>
            </div>
          );
        })}

        {/* Interactive Detail Drawer for Selected Shipment */}
        {selectedShipment && (
          <div
            className="glass-panel"
            style={{
              position: "absolute",
              right: "16px",
              bottom: "16px",
              width: "320px",
              padding: "16px",
              zIndex: 30,
              background: "rgba(15, 23, 42, 0.92)",
              border: "1px solid var(--accent-cyan)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
              <div>
                <span className="badge badge-cyan" style={{ fontSize: "9px", marginBottom: "4px" }}>
                  Selected Vehicle
                </span>
                <h3 style={{ fontSize: "14px", fontWeight: 700 }}>
                  {selectedShipment.tracking_number}
                </h3>
              </div>
              <span
                className={`badge badge-${selectedShipment.status === "at_risk" ? "rose" : "emerald"}`}
                style={{ fontSize: "10px" }}
              >
                {selectedShipment.status.replace("_", " ")}
              </span>
            </div>

            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px", display: "grid", gap: "6px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Route Corridor:</span>
                <span style={{ color: "#fff", fontWeight: 500 }}>
                  {selectedShipment.origin} → {selectedShipment.destination}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Carrier:</span>
                <span style={{ color: "#fff" }}>{selectedShipment.carrier?.name || "Apex Freight"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Cargo Value:</span>
                <span style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>
                  ${(selectedShipment.cargo_value_usd || 0).toLocaleString()}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Risk Score:</span>
                <span style={{ color: selectedShipment.risk_score > 70 ? "var(--accent-rose)" : "#fff", fontWeight: 700 }}>
                  {selectedShipment.risk_score} / 100 ({selectedShipment.risk_level.toUpperCase()})
                </span>
              </div>
            </div>

            {onSimulateShipment && (
              <button
                onClick={() => onSimulateShipment(selectedShipment)}
                className="btn-primary"
                style={{ width: "100%", justifyContent: "center", fontSize: "12px", padding: "8px" }}
              >
                <Zap size={14} />
                <span>Simulate Alternative Corridor</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
