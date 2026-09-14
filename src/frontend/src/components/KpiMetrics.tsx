"use client";

import React from "react";
import {
  AlertOctagon,
  ArrowDownRight,
  ArrowUpRight,
  DollarSign,
  Package,
  ShieldAlert,
  ThermometerSnowflake,
  TrendingDown,
  Truck,
  Zap,
} from "lucide-react";
import { Shipment, Disruption, FleetSummary, Recommendation } from "../lib/types";

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
  const coldChainShipments = shipments.filter((s) => s.temperature_required).length;

  const pendingApprovals = recommendations.filter((r) => r.status === "pending").length;
  const totalPotentialSavings = recommendations.reduce(
    (acc, r) => acc + (r.estimated_savings_usd || 0),
    0
  );

  const kpis = [
    {
      id: "active_shipments",
      title: "Active Shipments",
      value: shipments.length.toString(),
      subtext: `$${(totalCargoValue / 1000).toFixed(0)}k cargo in transit`,
      icon: Package,
      badge: "100% Tracked",
      badgeType: "cyan",
      borderGlow: "var(--border-glow)",
    },
    {
      id: "at_risk",
      title: "Disruption Exposure",
      value: atRiskCount.toString(),
      subtext: `${disruptions.length} active global incidents`,
      icon: ShieldAlert,
      badge: atRiskCount > 0 ? "Action Required" : "Nominal",
      badgeType: atRiskCount > 0 ? "rose" : "emerald",
      isPulse: atRiskCount > 0,
      onClick: onFilterAtRisk,
    },
    {
      id: "cold_chain",
      title: "Cold Chain Telematics",
      value: `${coldChainShipments} Units`,
      subtext: "1 Active Excursion (>8.0°C)",
      icon: ThermometerSnowflake,
      badge: "Real-time IoT",
      badgeType: "amber",
    },
    {
      id: "fleet_util",
      title: "Fleet Utilization",
      value: `${fleetSummary.average_utilisation_percent.toFixed(1)}%`,
      subtext: `${fleetSummary.available_count} available (${fleetSummary.refrigerated_available} Reefer)`,
      icon: Truck,
      badge: `${fleetSummary.idle_count} Idle Asset`,
      badgeType: "cyan",
    },
    {
      id: "prevented_loss",
      title: "Mitigated SLA Exposure",
      value: `$${(totalPotentialSavings / 1000).toFixed(0)}k`,
      subtext: `${pendingApprovals} pending AI approvals`,
      icon: DollarSign,
      badge: "+9.5h Delay Avoided",
      badgeType: "emerald",
    },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "14px",
        margin: "0 20px 20px 20px",
      }}
    >
      {kpis.map((kpi) => {
        const Icon = kpi.icon;
        return (
          <div
            key={kpi.id}
            onClick={kpi.onClick}
            className={`glass-panel ${kpi.isPulse ? "pulse-red" : ""}`}
            style={{
              padding: "16px 18px",
              cursor: kpi.onClick ? "pointer" : "default",
              position: "relative",
              overflow: "hidden",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 500 }}>
                {kpi.title}
              </span>
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "8px",
                  background: "rgba(255, 255, 255, 0.05)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: kpi.badgeType === "rose" ? "var(--accent-rose)" : "var(--accent-cyan)",
                }}
              >
                <Icon size={18} />
              </div>
            </div>

            <div style={{ fontSize: "24px", fontWeight: 700, marginBottom: "4px" }} className="brand-font">
              {kpi.value}
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "8px" }}>
              <span style={{ fontSize: "11px", color: "var(--text-faint)" }}>
                {kpi.subtext}
              </span>
              <span className={`badge badge-${kpi.badgeType}`} style={{ fontSize: "9px" }}>
                {kpi.badge}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
