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
    } catch (err) {
      console.warn("Using offline fallback data");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSimulateFromMap = (s: Shipment) => {
    setSelectedShipment(s);
    setActiveTab("simulation");
  };

  const handleTriggerReeferSwap = (s: Shipment) => {
    setSelectedShipment(s);
    setActiveTab("recommendations");
  };

  return (
    <main style={{ minHeight: "100vh", paddingBottom: "40px" }}>
      {/* Top Header Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isLive={isLive}
        activeDisruptionsCount={disruptions.filter((d) => d.status === "active").length}
        pendingRecsCount={recommendations.filter((r) => r.status === "pending").length}
        onRefresh={loadData}
        isRefreshing={isRefreshing}
      />

      {/* KPI Metrics Strip */}
      <KpiMetrics
        shipments={shipments}
        disruptions={disruptions}
        fleetSummary={fleetSummary}
        recommendations={recommendations}
        onFilterAtRisk={() => setActiveTab("overview")}
      />

      {/* Tab View Routing */}
      {activeTab === "overview" && (
        <>
          <ControlTowerMap
            shipments={shipments}
            disruptions={disruptions}
            selectedShipment={selectedShipment}
            onSelectShipment={setSelectedShipment}
            onSimulateShipment={handleSimulateFromMap}
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(450px, 1fr))", gap: "0px" }}>
            <RecommendationsPanel
              recommendations={recommendations}
              onRecommendationUpdated={loadData}
            />
            <ColdChainMonitor
              shipments={shipments}
              onTriggerReeferSwap={handleTriggerReeferSwap}
            />
          </div>
        </>
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
          onTriggerReeferSwap={handleTriggerReeferSwap}
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
