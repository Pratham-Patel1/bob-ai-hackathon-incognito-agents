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

          {/* Right Column: Pharma Reroute Action & Cold Chain Monitor */}
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <RecommendationsPanel
              recommendations={recommendations}
              filterId="rec-01"
              hideHeader={true}
              noMargin={true}
              onRecommendationUpdated={loadData}
            />

            <ColdChainMonitor
              shipments={shipments}
              onTriggerReeferSwap={() => setActiveTab("recommendations")}
            />
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
