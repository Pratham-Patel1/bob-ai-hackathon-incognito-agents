"use client";

import React from "react";
import {
  Activity,
  AlertTriangle,
  Compass,
  Cpu,
  History,
  Layers,
  Radio,
  RefreshCw,
  ShieldCheck,
  Truck,
} from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isLive: boolean;
  activeDisruptionsCount: number;
  pendingRecsCount: number;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export default function Navbar({
  activeTab,
  setActiveTab,
  isLive,
  activeDisruptionsCount,
  pendingRecsCount,
  onRefresh,
  isRefreshing,
}: NavbarProps) {
  const navItems = [
    { id: "overview", label: "Control Tower", icon: Compass },
    { id: "simulation", label: "Digital Twin", icon: Cpu },
    { id: "coldchain", label: "Cold Chain IoT", icon: Activity },
    { id: "recommendations", label: "AI Copilot & HITL", icon: ShieldCheck, badge: pendingRecsCount },
    { id: "fleet", label: "Fleet Telematics", icon: Truck },
    { id: "audit", label: "Audit Compliance", icon: History },
  ];

  return (
    <header className="glass-panel" style={{ margin: "16px 20px", padding: "12px 24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
        
        {/* Brand & Subtitle */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 20px rgba(0, 242, 254, 0.4)",
            }}
          >
            <Layers size={22} color="#040d21" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h1 style={{ fontSize: "19px", fontWeight: 700, letterSpacing: "-0.02em" }}>
                SupplyChain<span style={{ color: "var(--accent-cyan)" }}>OS</span>
              </h1>
              <span className="badge badge-purple" style={{ fontSize: "10px" }}>
                v1.0 • Control Tower
              </span>
            </div>
            <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              AI-Powered Supply Chain Resilience & Digital Twin Control
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: "flex", gap: "6px", overflowX: "auto", padding: "4px" }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  background: isActive ? "rgba(0, 242, 254, 0.12)" : "transparent",
                  color: isActive ? "var(--accent-cyan)" : "var(--text-muted)",
                  border: isActive ? "1px solid rgba(0, 242, 254, 0.35)" : "1px solid transparent",
                  padding: "8px 14px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: isActive ? 600 : 500,
                  display: "flex",
                  alignItems: "center",
                  gap: "7px",
                  transition: "all 0.15s ease",
                  whiteSpace: "nowrap",
                }}
              >
                <Icon size={15} />
                {item.label}
                {item.badge !== undefined && item.badge > 0 && (
                  <span
                    style={{
                      background: "var(--accent-rose)",
                      color: "#fff",
                      fontSize: "10px",
                      borderRadius: "10px",
                      padding: "1px 6px",
                      fontWeight: 700,
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Live Status Pill & Quick Action */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {activeDisruptionsCount > 0 && (
            <div className="badge badge-rose" style={{ padding: "6px 12px", display: "flex", gap: "6px" }}>
              <AlertTriangle size={13} />
              <span>{activeDisruptionsCount} Active Disruptions</span>
            </div>
          )}

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 12px",
              borderRadius: "20px",
              background: isLive ? "rgba(16, 185, 129, 0.1)" : "rgba(245, 158, 11, 0.1)",
              border: isLive ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid rgba(245, 158, 11, 0.3)",
              fontSize: "12px",
              fontWeight: 500,
              color: isLive ? "var(--accent-emerald)" : "var(--accent-amber)",
            }}
          >
            <div
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: isLive ? "var(--accent-emerald)" : "var(--accent-amber)",
                boxShadow: isLive ? "0 0 8px #10b981" : "0 0 8px #f59e0b",
              }}
            />
            <span>{isLive ? "FastAPI Gateway Online" : "Demo Data Cache"}</span>
          </div>

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="btn-secondary"
            title="Refresh pipeline data"
            style={{ padding: "7px 12px" }}
          >
            <RefreshCw size={14} className={isRefreshing ? "animate-spin" : ""} />
            <span style={{ fontSize: "12px" }}>Sync</span>
          </button>
        </div>

      </div>
    </header>
  );
}
