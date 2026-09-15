"use client";

import React from "react";
import {
  AlertTriangle,
  Clock,
  DollarSign,
  Package,
  ShieldAlert,
  Snowflake,
  TrendingDown,
  Truck,
} from "lucide-react";
import { Shipment, Disruption, FleetSummary, Recommendation } from "../lib/types";
import { formatCurrency } from "../lib/api";

interface KpiMetricsProps {
  shipments: Shipment[];
  disruptions: Disruption[];
  fleetSummary: FleetSummary;
  recommendations: Recommendation[];
  onFilterAtRisk?: () => void;
}

export default function KpiMetrics({
  shipments,
  disruptions,
  fleetSummary,
  recommendations,
  onFilterAtRisk,
}: KpiMetricsProps) {
  const atRiskCount = shipments.filter(
    (s) => s.status === "at_risk" || s.risk_level === "high" || s.risk_level === "critical"
  ).length;

  const totalCargoValue = shipments.reduce((acc, s) => acc + (s.cargo_value_usd || 0), 0);
  const totalSavings = recommendations.reduce((acc, r) => acc + (r.estimated_savings_usd || 0), 0);

  const kpiList = [
    {
      id: "active",
      label: "Active In-Transit",
      value: `${shipments.length} Cargoes`,
      highlight: formatCurrency(totalCargoValue) + " Value",
      icon: Package,
      color: "var(--accent-cyan)",
    },
    {
      id: "risk",
      label: "At-Risk Disrupted",
      value: `${atRiskCount} Shipment`,
      highlight: "North Sea Gale Alert",
      icon: ShieldAlert,
      color: "var(--accent-rose)",
      isAlert: atRiskCount > 0,
      onClick: onFilterAtRisk,
    },
    {
      id: "coldchain",
      label: "Cold-Chain Telemetry",
      value: "1 Excursion",
      highlight: "+8.9°C Spike Kassel Hub",
      icon: Snowflake,
      color: "var(--accent-amber)",
    },
    {
      id: "mitigated",
      label: "Mitigated Delay & Loss",
      value: formatCurrency(totalSavings),
      highlight: "-9.5h Delay Avoided",
      icon: DollarSign,
      color: "var(--accent-emerald)",
    },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: "12px",
        margin: "0 20px 16px 20px",
      }}
    >
      {kpiList.map((kpi) => {
        const Icon = kpi.icon;
        return (
          <div
            key={kpi.id}
            onClick={kpi.onClick}
            className="glass-panel"
            style={{
              padding: "12px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              cursor: kpi.onClick ? "pointer" : "default",
              border: kpi.isAlert ? "1px solid rgba(244, 63, 94, 0.4)" : "1px solid var(--border-subtle)",
              background: kpi.isAlert ? "rgba(244, 63, 94, 0.05)" : "var(--bg-surface)",
            }}
          >
            <div>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "block" }}>
                {kpi.label}
              </span>
              <div style={{ fontSize: "18px", fontWeight: 700, color: "#fff", marginTop: "2px" }}>
                {kpi.value}
              </div>
              <span style={{ fontSize: "10px", color: kpi.color, fontWeight: 500, marginTop: "2px", display: "block" }}>
                {kpi.highlight}
              </span>
            </div>

            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "rgba(255, 255, 255, 0.04)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: kpi.color,
              }}
            >
              <Icon size={18} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
