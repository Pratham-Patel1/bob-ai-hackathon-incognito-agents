"use client";

import React, { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import KpiMetrics from "../components/KpiMetrics";
import ControlTowerMap from "../components/ControlTowerMap";
import ColdChainMonitor from "../components/ColdChainMonitor";
import SimulationStudio from "../components/SimulationStudio";
import RecommendationsPanel from "../components/RecommendationsPanel";
import AuditLogTable from "../components/AuditLogTable";
import FleetPanel from "../components/FleetPanel";
import { AlertTriangle, ArrowRight } from "lucide-react";

import {
  Shipment,
  Disruption,
  FleetVehicle,
  FleetSummary,
  Recommendation,
  DecisionAudit,
} from "../lib/types";
import {
  getShipments,
  getDisruptions,
  getFleet,
  getFleetIntelligence,
  getRecommendations,
  getAuditLogs,
  MOCK_SHIPMENTS,
  MOCK_DISRUPTIONS,
  MOCK_FLEET,
  MOCK_RECOMMENDATIONS,
  MOCK_AUDIT_LOGS,
} from "../lib/api";

export default function ControlTowerHome() {
  const [mounted, setMounted] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [isLive, setIsLive] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const [shipments, setShipments] = useState<Shipment[]>(MOCK_SHIPMENTS);
  const [disruptions, setDisruptions] = useState<Disruption[]>(MOCK_DISRUPTIONS);
  const [fleet, setFleet] = useState<FleetVehicle[]>(MOCK_FLEET);
  const [fleetSummary, setFleetSummary] = useState<FleetSummary>({
    total_vehicles: 6,
    idle_count: 1,
    available_count: 2,
    overloaded_count: 1,
    in_transit_count: 2,
    maintenance_count: 0,
    average_utilisation_percent: 54.2,
    refrigerated_available: 1,
  });
  const [recommendations, setRecommendations] = useState<Recommendation[]>(MOCK_RECOMMENDATIONS);
  const [auditLogs, setAuditLogs] = useState<DecisionAudit[]>(MOCK_AUDIT_LOGS);
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(MOCK_SHIPMENTS[0]);

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      const [sRes, dRes, fRes, fiRes, rRes, aRes] = await Promise.all([
        getShipments(),
        getDisruptions(),
        getFleet(),
        getFleetIntelligence(),
        getRecommendations(),
        getAuditLogs(),
      ]);

      setShipments(sRes.shipments);
      setDisruptions(dRes.disruptions);
      setFleet(fRes.fleet);
      setFleetSummary(fiRes.summary);
      setRecommendations(rRes.recommendations);
      setAuditLogs(aRes.logs);
      setIsLive(sRes.isLive);

      if (sRes.shipments.length > 0) {
        setSelectedShipment(sRes.shipments[0]);
      }
    } catch {
      // Offline fallback
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    setMounted(true);
    loadData();
  }, []);

  // Hydration protection
  if (!mounted) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "#080c14",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ color: "var(--accent-cyan)", fontSize: "14px", fontWeight: 600, letterSpacing: "0.05em" }}>
          Initializing SupplyChainOS Control Tower...
        </div>
      </div>
    );
  }

  const handleSimulateFromMap = (s: Shipment) => {
    setSelectedShipment(s);
    setActiveTab("simulation");
  };

  return (
    <main style={{ minHeight: "100vh", paddingBottom: "30px" }}>
      {/* 1. Sleek Navigation Header */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isLive={isLive}
        activeDisruptionsCount={disruptions.filter((d) => d.status === "active").length}
        pendingRecsCount={recommendations.filter((r) => r.status === "pending").length}
        onRefresh={loadData}
        isRefreshing={isRefreshing}
      />

      {/* 2. Focused Executive Metrics (4 Balanced Cards) */}
      <KpiMetrics
        shipments={shipments}
        disruptions={disruptions}
        fleetSummary={fleetSummary}
        recommendations={recommendations}
        onFilterAtRisk={() => setActiveTab("overview")}
      />

      {/* 3. Main Body Content */}
      {activeTab === "overview" && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.5fr 1fr",
            gap: "16px",
            margin: "0 20px",
          }}
        >
          {/* Left Column: Digital Twin Map + Carrier Swap Panel Below It */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <ControlTowerMap
              shipments={shipments}
              disruptions={disruptions}
              selectedShipment={selectedShipment}
              onSelectShipment={setSelectedShipment}
              onSimulateShipment={handleSimulateFromMap}
            />

            {/* Carrier Swap Panel filling the empty section below the Map */}
            <RecommendationsPanel
              recommendations={recommendations}
              filterId="rec-02"
              hideHeader={true}
              noMargin={true}
              onRecommendationUpdated={loadData}
            />
          </div>

          {/* Right Column: Pharma Reroute Action & Live Corridor Threat Intel */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <RecommendationsPanel
              recommendations={recommendations}
              filterId="rec-01"
              hideHeader={true}
              noMargin={true}
              onRecommendationUpdated={loadData}
            />

            {/* Active Corridor Disruptions Threat Intel Feed */}
            <div className="glass-panel" style={{ padding: "18px", display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "8px",
                      background: "rgba(244, 63, 94, 0.15)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "var(--accent-rose)",
                    }}
                  >
                    <AlertTriangle size={18} />
                  </div>
                  <div>
                    <h3 style={{ fontSize: "14px", fontWeight: 700, letterSpacing: "-0.01em" }}>
                      Active Corridor Threat Intel
                    </h3>
                    <p style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      Live atmospheric & infrastructure telemetry affecting active freight lanes
                    </p>
                  </div>
                </div>
                <span className="badge badge-rose">
                  {disruptions.filter((d) => d.status === "active").length} Active Alerts
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {disruptions.slice(0, 3).map((d) => {
                  const isCritical = d.severity === "critical";
                  return (
                    <div
                      key={d.id}
                      style={{
                        padding: "12px 14px",
                        borderRadius: "10px",
                        background: "rgba(14, 20, 36, 0.6)",
                        border: isCritical ? "1px solid rgba(244, 63, 94, 0.3)" : "1px solid var(--border-subtle)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "6px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span className={`badge ${isCritical ? "badge-rose" : "badge-amber"}`} style={{ fontSize: "10px", padding: "2px 8px" }}>
                            {d.severity.toUpperCase()}
                          </span>
                          <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-main)" }}>
                            {d.title}
                          </span>
                        </div>
                        <span style={{ fontSize: "11px", color: isCritical ? "var(--accent-rose)" : "var(--accent-amber)", fontWeight: 700 }}>
                          +{d.estimated_delay_hours}h Delay
                        </span>
                      </div>

                      <p style={{ fontSize: "12px", color: "var(--text-muted)", lineHeight: 1.4 }}>
                        {d.description}
                      </p>

                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
                        <span style={{ fontSize: "11px", color: "var(--text-faint)" }}>
                          Blast Radius: <strong style={{ color: "var(--text-muted)" }}>{d.affected_radius_km} km</strong>
                        </span>
                        <button
                          onClick={() => {
                            const matchShipment = shipments.find((s) => s.status === "at_risk" || s.status === "delayed") || shipments[0];
                            if (matchShipment) handleSimulateFromMap(matchShipment);
                          }}
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--accent-cyan)",
                            fontSize: "11px",
                            fontWeight: 600,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          Simulate Response <ArrowRight size={12} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "simulation" && (
        <SimulationStudio
          shipments={shipments}
          onCommitSimulation={() => setActiveTab("recommendations")}
        />
      )}

      {activeTab === "coldchain" && (
        <ColdChainMonitor
          shipments={shipments}
          onTriggerReeferSwap={() => setActiveTab("recommendations")}
        />
      )}

      {activeTab === "recommendations" && (
        <RecommendationsPanel
          recommendations={recommendations}
          onRecommendationUpdated={loadData}
        />
      )}

      {activeTab === "fleet" && (
        <FleetPanel fleet={fleet} summary={fleetSummary} />
      )}

      {activeTab === "audit" && (
        <AuditLogTable logs={auditLogs} />
      )}
    </main>
  );
}
