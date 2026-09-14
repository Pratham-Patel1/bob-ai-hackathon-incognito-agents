"use client";

import React from "react";
import {
  Activity,
  AlertTriangle,
  Compass,
  Cpu,
  History,
  Layers,
  Plus,
  RefreshCw,
  ShieldCheck,
  Truck,
  Zap,
} from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isLive: boolean;
  activeDisruptionsCount: number;
  pendingRecsCount: number;
  onRefresh: () => void;
  isRefreshing: boolean;
  onOpenInjectDisruption?: () => void;
  onOpenAssessShipment?: () => void;
}

export default function Navbar({
  activeTab,
  setActiveTab,
  isLive,
  activeDisruptionsCount,
  pendingRecsCount,
  onRefresh,
  isRefreshing,
  onOpenInjectDisruption,
  onOpenAssessShipment,
}: NavbarProps) {
  const navTabs = [
    { id: "overview", label: "Control Tower", icon: Compass },
    { id: "simulation", label: "Digital Twin", icon: Cpu },
    { id: "coldchain", label: "Cold Chain", icon: Activity },
    { id: "recommendations", label: "AI Copilot", icon: ShieldCheck, badge: pendingRecsCount },
    { id: "fleet", label: "Fleet", icon: Truck },
    { id: "audit", label: "Audit", icon: History },
  ];

  return (
    <header
      className="glass-panel"
      style={{
        margin: "14px 20px",
        padding: "10px 20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "16px",
      }}
    >
      {/* 1. Left: Brand Logo & Title */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: "200px" }}>
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            background: "linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 14px rgba(0, 242, 254, 0.3)",
          }}
        >
          <Layers size={18} color="#040d21" strokeWidth={2.5} />
        </div>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "16px", fontWeight: 700, letterSpacing: "-0.02em" }}>
              SupplyChain<span style={{ color: "var(--accent-cyan)" }}>OS</span>
            </span>
          </div>
          <p style={{ fontSize: "10px", color: "var(--text-faint)" }}>
            Digital Twin Resilience
          </p>
        </div>
      </div>

      {/* 2. Center: Sleek Segmented Pill Navigation */}
      <nav
        style={{
          display: "flex",
          background: "rgba(0, 0, 0, 0.25)",
          padding: "4px",
          borderRadius: "10px",
          border: "1px solid rgba(255, 255, 255, 0.05)",
          gap: "2px",
        }}
      >
        {navTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: isActive ? "rgba(0, 242, 254, 0.12)" : "transparent",
                color: isActive ? "var(--accent-cyan)" : "var(--text-muted)",
                border: isActive ? "1px solid rgba(0, 242, 254, 0.3)" : "1px solid transparent",
                padding: "6px 14px",
                borderRadius: "7px",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: isActive ? 600 : 500,
                display: "flex",
                alignItems: "center",
                gap: "6px",
                transition: "all 0.15s ease",
              }}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
              {tab.badge !== undefined && tab.badge > 0 && (
                <span
                  style={{
                    background: "var(--accent-rose)",
                    color: "#fff",
                    fontSize: "9px",
                    borderRadius: "8px",
                    padding: "1px 5px",
                    fontWeight: 700,
                  }}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* 3. Right: Interactive Actions & Status */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", justifyContent: "flex-end" }}>
        {onOpenAssessShipment && (
          <button
            onClick={onOpenAssessShipment}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              padding: "5px 11px",
              borderRadius: "7px",
              background: "rgba(0, 242, 254, 0.08)",
              border: "1px solid rgba(0, 242, 254, 0.3)",
              color: "var(--accent-cyan)",
              fontSize: "11px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
            title="Evaluate custom shipment risk using client-side ML"
          >
            <Plus size={13} />
            <span>Assess Risk</span>
          </button>
        )}

        {onOpenInjectDisruption && (
          <button
            onClick={onOpenInjectDisruption}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              padding: "5px 11px",
              borderRadius: "7px",
              background: "rgba(244, 63, 94, 0.12)",
              border: "1px solid rgba(244, 63, 94, 0.35)",
              color: "var(--accent-rose)",
              fontSize: "11px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
            title="Simulate a real-time disruption event and watch the AI react"
          >
            <Zap size={13} />
            <span>Inject Threat</span>
          </button>
        )}

        {activeDisruptionsCount > 0 && (
          <div
            title={`${activeDisruptionsCount} active disruption events`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              padding: "4px 10px",
              borderRadius: "20px",
              background: "rgba(244, 63, 94, 0.12)",
              border: "1px solid rgba(244, 63, 94, 0.3)",
              fontSize: "11px",
              color: "var(--accent-rose)",
              fontWeight: 600,
            }}
          >
            <AlertTriangle size={12} />
            <span>{activeDisruptionsCount} Alerts</span>
          </div>
        )}

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            padding: "4px 10px",
            borderRadius: "20px",
            background: isLive ? "rgba(16, 185, 129, 0.08)" : "rgba(245, 158, 11, 0.08)",
            border: isLive ? "1px solid rgba(16, 185, 129, 0.25)" : "1px solid rgba(245, 158, 11, 0.25)",
            fontSize: "11px",
            color: isLive ? "var(--accent-emerald)" : "var(--accent-amber)",
          }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: isLive ? "var(--accent-emerald)" : "var(--accent-amber)",
            }}
          />
          <span>{isLive ? "Live" : "Demo Mode"}</span>
        </div>

        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="btn-secondary"
          title="Sync live data"
          style={{ padding: "6px 10px", fontSize: "11px", borderRadius: "6px" }}
        >
          <RefreshCw size={12} className={isRefreshing ? "animate-spin" : ""} />
        </button>
      </div>
    </header>
  );
}
