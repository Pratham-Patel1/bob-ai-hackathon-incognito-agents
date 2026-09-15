"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  Cpu,
  Gauge,
  MapPin,
  RefreshCw,
  Snowflake,
  Truck,
  Zap,
} from "lucide-react";
import { FleetVehicle, FleetSummary } from "../lib/types";

interface FleetPanelProps {
  fleet: FleetVehicle[];
  summary: FleetSummary;
}

export default function FleetPanel({ fleet, summary }: FleetPanelProps) {
  const [filterType, setFilterType] = useState<string>("all");

  const filteredFleet = fleet.filter((v) => {
    if (filterType === "all") return true;
    if (filterType === "available") return v.status === "available";
    if (filterType === "idle") return v.status === "idle" || (v.utilisation_percent && v.utilisation_percent < 20);
    if (filterType === "reefer") return v.is_refrigerated;
    return true;
  });

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
            <Truck size={20} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h2 style={{ fontSize: "16px", fontWeight: 700 }}>
                Fleet Intelligence & Telematics Hub
              </h2>
              <span className="badge badge-cyan">Dynamic Redeployment</span>
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              Real-time asset matching across idle capacity, reefer units, and proximity corridors
            </p>
          </div>
        </div>

        {/* Filters */}
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={() => setFilterType("all")}
            className={filterType === "all" ? "btn-primary" : "btn-secondary"}
            style={{ fontSize: "11px", padding: "6px 12px" }}
          >
            All Vehicles ({fleet.length})
          </button>
          <button
            onClick={() => setFilterType("available")}
            className={filterType === "available" ? "btn-primary" : "btn-secondary"}
            style={{ fontSize: "11px", padding: "6px 12px" }}
          >
            Available ({summary.available_count})
          </button>
          <button
            onClick={() => setFilterType("idle")}
            className={filterType === "idle" ? "btn-primary" : "btn-secondary"}
            style={{ fontSize: "11px", padding: "6px 12px" }}
          >
            Idle Assets ({summary.idle_count})
          </button>
          <button
            onClick={() => setFilterType("reefer")}
            className={filterType === "reefer" ? "btn-primary" : "btn-secondary"}
            style={{ fontSize: "11px", padding: "6px 12px" }}
          >
            Reefer Units ({summary.refrigerated_available})
          </button>
        </div>
      </div>

      {/* Fleet Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "14px" }}>
        {filteredFleet.map((vehicle) => {
          const util = vehicle.utilisation_percent ?? (vehicle.current_load_tons / (vehicle.capacity_tons || 1)) * 100;
          const isOverloaded = util > 95;
          const isIdle = util < 20;

          return (
            <div
              key={vehicle.id}
              className="glass-panel"
              style={{
                padding: "16px 18px",
                border: vehicle.suitability_score && vehicle.suitability_score > 90
                  ? "1px solid var(--accent-cyan)"
                  : "1px solid var(--border-subtle)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                    <span style={{ fontSize: "15px", fontWeight: 700, color: "#fff" }}>
                      {vehicle.vehicle_code}
                    </span>
                    {vehicle.is_refrigerated && (
                      <span className="badge badge-cyan" style={{ fontSize: "9px" }}>
                        <Snowflake size={10} /> REEFER
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "capitalize" }}>
                    {vehicle.vehicle_type.replace("_", " ")}
                  </span>
                </div>

                <span
                  className={`badge badge-${
                    vehicle.status === "available"
                      ? "emerald"
                      : vehicle.status === "idle"
                      ? "amber"
                      : "purple"
                  }`}
                  style={{ fontSize: "9px" }}
                >
                  {vehicle.status.toUpperCase()}
                </span>
              </div>

              {/* Progress Bar for Utilisation */}
              <div style={{ marginBottom: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "4px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Utilisation:</span>
                  <span style={{ fontWeight: 600, color: isOverloaded ? "var(--accent-rose)" : isIdle ? "var(--accent-amber)" : "var(--accent-emerald)" }}>
                    {util.toFixed(1)}% ({vehicle.current_load_tons} / {vehicle.capacity_tons} T)
                  </span>
                </div>
                <div style={{ height: "6px", borderRadius: "3px", background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.min(100, util)}%`,
                      background: isOverloaded
                        ? "var(--accent-rose)"
                        : isIdle
                        ? "var(--accent-amber)"
                        : "var(--accent-emerald)",
                      transition: "width 0.4s ease",
                    }}
                  />
                </div>
              </div>

              {/* Proximity & Suitability */}
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-faint)", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
                <span>GPS: {vehicle.latitude.toFixed(2)}°N, {vehicle.longitude.toFixed(2)}°E</span>
                {vehicle.suitability_score ? (
                  <span style={{ color: "var(--accent-cyan)", fontWeight: 700 }}>
                    Match: {vehicle.suitability_score}%
                  </span>
                ) : (
                  <span>Ready</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
