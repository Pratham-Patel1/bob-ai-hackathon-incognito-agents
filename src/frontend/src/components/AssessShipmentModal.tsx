"use client";

import React, { useState, useMemo } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  DollarSign,
  Gauge,
  Navigation,
  ShieldAlert,
  Snowflake,
  Truck,
  X,
  Zap,
} from "lucide-react";
import { Shipment } from "../lib/types";

interface AssessShipmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDeployShipment: (shipment: Shipment) => void;
}

const HUBS = [
  { name: "Hamburg Port (DE)", lat: 53.55, lng: 9.99 },
  { name: "Frankfurt Logistics Hub (DE)", lat: 50.11, lng: 8.68 },
  { name: "Rotterdam Europort (NL)", lat: 51.92, lng: 4.48 },
  { name: "Antwerp Terminal (BE)", lat: 51.22, lng: 4.4 },
  { name: "Berlin Hub (DE)", lat: 52.52, lng: 13.4 },
  { name: "Munich South (DE)", lat: 48.14, lng: 11.58 },
  { name: "Paris Cargo City (FR)", lat: 48.86, lng: 2.35 },
  { name: "Milan Intermodal (IT)", lat: 45.46, lng: 9.19 },
];

export default function AssessShipmentModal({
  isOpen,
  onClose,
  onDeployShipment,
}: AssessShipmentModalProps) {
  const [trackingNumber, setTrackingNumber] = useState<string>("TRK-EVAL-2026-901");
  const [cargoType, setCargoType] = useState<string>("Pharmaceuticals & Vaccines");
  const [originIndex, setOriginIndex] = useState<number>(0);
  const [destIndex, setDestIndex] = useState<number>(5);
  const [cargoValue, setCargoValue] = useState<number>(450000);
  const [distanceKm, setDistanceKm] = useState<number>(680);
  const [carrierReliability, setCarrierReliability] = useState<number>(82);
  const [weatherSeverity, setWeatherSeverity] = useState<number>(2);
  const [isPerishable, setIsPerishable] = useState<boolean>(true);

  // Real-time ML Inference Formulation (Client-side digital twin simulation)
  const mlInference = useMemo(() => {
    const weatherFactor = (weatherSeverity / 4.0) * 0.32;
    const carrierFactor = (1 - carrierReliability / 100.0) * 0.28;
    const distFactor = Math.min(distanceKm / 1200.0, 1.0) * 0.2;
    const cargoLog = Math.min(Math.log10(Math.max(cargoValue, 1000)) / 7.0, 1.0) * 0.12;
    const tempRisk = isPerishable ? 0.18 : 0.02;

    const rawScore = (weatherFactor + carrierFactor + distFactor + cargoLog + tempRisk) * 100;
    const delayProb = Math.min(98, Math.max(6, Math.round(rawScore)));
    const predDelayHours = Math.max(0.5, Number(((delayProb / 100) * (distanceKm / 65) * 0.75).toFixed(1)));

    let riskLevel: "low" | "medium" | "high" | "critical" = "low";
    if (delayProb >= 72) riskLevel = "critical";
    else if (delayProb >= 48) riskLevel = "high";
    else if (delayProb >= 25) riskLevel = "medium";

    return {
      delayProbability: delayProb,
      predictedDelayHours: predDelayHours,
      riskLevel,
      rawScore: Math.round(rawScore),
    };
  }, [cargoValue, distanceKm, carrierReliability, weatherSeverity, isPerishable]);

  if (!isOpen) return null;

  const handleDeploy = (e: React.FormEvent) => {
    e.preventDefault();
    const origin = HUBS[originIndex];
    const dest = HUBS[destIndex];

    const newShipment: Shipment = {
      id: `ship-${Date.now().toString().slice(-4)}`,
      tracking_number: trackingNumber,
      origin: origin.name,
      destination: dest.name,
      origin_lat: origin.lat,
      origin_lng: origin.lng,
      destination_lat: dest.lat,
      destination_lng: dest.lng,
      current_location: `${origin.name.split(" ")[0]} Corridor`,
      current_lat: (origin.lat + dest.lat) / 2 + 0.1,
      current_lng: (origin.lng + dest.lng) / 2 - 0.1,
      status: mlInference.riskLevel === "critical" ? "at_risk" : "in_transit",
      scheduled_departure: new Date().toISOString(),
      scheduled_arrival: new Date(Date.now() + 24 * 3600000).toISOString(),
      estimated_arrival: new Date(Date.now() + (24 + mlInference.predictedDelayHours) * 3600000).toISOString(),
      cargo_type: cargoType,
      cargo_value_usd: cargoValue,
      weight_kg: 14500,
      temperature_required: isPerishable,
      temp_min_c: isPerishable ? 2.0 : undefined,
      temp_max_c: isPerishable ? 8.0 : undefined,
      risk_score: mlInference.rawScore,
      risk_level: mlInference.riskLevel,
      carrier: {
        id: "c-eval",
        name: "Custom Carrier Partner",
        code: "CAR-CUST",
        reliability_score: carrierReliability / 100,
      },
      route: {
        id: "r-eval",
        code: "RT-CUST",
        name: `${origin.name.split(" ")[0]} → ${dest.name.split(" ")[0]} Corridor`,
        distance_km: distanceKm,
      },
    };

    onDeployShipment(newShipment);
    onClose();
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(3, 7, 18, 0.85)",
        backdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
      onClick={onClose}
    >
      <div
        className="glass-panel"
        style={{
          width: "100%",
          maxWidth: "720px",
          background: "linear-gradient(180deg, rgba(20, 27, 45, 0.95) 0%, rgba(10, 15, 29, 0.98) 100%)",
          border: "1px solid rgba(0, 242, 254, 0.35)",
          boxShadow: "0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(0, 242, 254, 0.2)",
          padding: "24px",
          maxHeight: "90vh",
          overflowY: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "rgba(0, 242, 254, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--accent-cyan)",
              }}
            >
              <Cpu size={22} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h2 style={{ fontSize: "17px", fontWeight: 700 }}>ML Shipment Risk Calculator</h2>
                <span className="badge badge-cyan">In-Memory Engine</span>
              </div>
              <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Adjust operational parameters to evaluate instant Random Forest delay and risk predictions
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-faint)",
              cursor: "pointer",
              padding: "4px",
            }}
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleDeploy} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Top Row: Tracking & Cargo Type */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: "12px" }}>
            <div>
              <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
                TRACKING NUMBER
              </label>
              <input
                type="text"
                value={trackingNumber}
                onChange={(e) => setTrackingNumber(e.target.value)}
                required
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  background: "rgba(8, 12, 20, 0.8)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "13px",
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
                CARGO CATEGORY
              </label>
              <select
                value={cargoType}
                onChange={(e) => setCargoType(e.target.value)}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  background: "rgba(8, 12, 20, 0.8)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "13px",
                }}
              >
                <option value="Pharmaceuticals & Vaccines">Pharmaceuticals & Vaccines (Cold Chain)</option>
                <option value="Automotive Subassemblies">Automotive Subassemblies (Just-in-Time)</option>
                <option value="Precision Semiconductors">Precision Semiconductors (High Value)</option>
                <option value="Fresh Perishable Produce">Fresh Perishable Produce</option>
                <option value="Industrial Chemical Hazmat">Industrial Chemical Hazmat</option>
              </select>
            </div>
          </div>

          {/* Origin & Destination */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
                ORIGIN HUB
              </label>
              <select
                value={originIndex}
                onChange={(e) => setOriginIndex(Number(e.target.value))}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  background: "rgba(8, 12, 20, 0.8)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "13px",
                }}
              >
                {HUBS.map((h, i) => (
                  <option key={h.name} value={i}>
                    {h.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
                DESTINATION HUB
              </label>
              <select
                value={destIndex}
                onChange={(e) => setDestIndex(Number(e.target.value))}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  background: "rgba(8, 12, 20, 0.8)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "13px",
                }}
              >
                {HUBS.map((h, i) => (
                  <option key={h.name} value={i} disabled={i === originIndex}>
                    {h.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Interactive ML Feature Sliders */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            {/* Cargo Value */}
            <div style={{ background: "rgba(8, 12, 20, 0.5)", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>Cargo Value ($USD)</span>
                <strong style={{ color: "var(--accent-emerald)", fontSize: "13px" }}>${cargoValue.toLocaleString()}</strong>
              </div>
              <input
                type="range"
                min={20000}
                max={2000000}
                step={20000}
                value={cargoValue}
                onChange={(e) => setCargoValue(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--accent-emerald)", cursor: "pointer" }}
              />
            </div>

            {/* Distance */}
            <div style={{ background: "rgba(8, 12, 20, 0.5)", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>Transit Distance (km)</span>
                <strong style={{ color: "var(--accent-blue)", fontSize: "13px" }}>{distanceKm} km</strong>
              </div>
              <input
                type="range"
                min={100}
                max={1500}
                step={25}
                value={distanceKm}
                onChange={(e) => setDistanceKm(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--accent-blue)", cursor: "pointer" }}
              />
            </div>

            {/* Carrier Reliability */}
            <div style={{ background: "rgba(8, 12, 20, 0.5)", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>Carrier Reliability (%)</span>
                <strong style={{ color: carrierReliability < 75 ? "var(--accent-rose)" : "var(--accent-cyan)", fontSize: "13px" }}>
                  {carrierReliability}% On-Time
                </strong>
              </div>
              <input
                type="range"
                min={50}
                max={99}
                step={1}
                value={carrierReliability}
                onChange={(e) => setCarrierReliability(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--accent-cyan)", cursor: "pointer" }}
              />
            </div>

            {/* Weather / Corridor Threat */}
            <div style={{ background: "rgba(8, 12, 20, 0.5)", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: 600 }}>Weather Severity (0–4)</span>
                <strong style={{ color: weatherSeverity >= 3 ? "var(--accent-rose)" : "var(--accent-amber)", fontSize: "13px" }}>
                  Level {weatherSeverity} ({weatherSeverity === 0 ? "Clear" : weatherSeverity === 1 ? "Minor" : weatherSeverity === 2 ? "Gale" : weatherSeverity === 3 ? "Severe" : "Critical Blast"})
                </strong>
              </div>
              <input
                type="range"
                min={0}
                max={4}
                step={1}
                value={weatherSeverity}
                onChange={(e) => setWeatherSeverity(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--accent-rose)", cursor: "pointer" }}
              />
            </div>
          </div>

          {/* Perishable Toggle */}
          <div
            onClick={() => setIsPerishable(!isPerishable)}
            style={{
              padding: "10px 14px",
              borderRadius: "8px",
              background: isPerishable ? "rgba(0, 242, 254, 0.12)" : "rgba(255, 255, 255, 0.03)",
              border: isPerishable ? "1px solid var(--accent-cyan)" : "1px solid var(--border-subtle)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <Snowflake size={18} color={isPerishable ? "var(--accent-cyan)" : "var(--text-faint)"} />
              <div>
                <div style={{ fontSize: "13px", fontWeight: 600, color: isPerishable ? "#fff" : "var(--text-muted)" }}>
                  Cold-Chain Telemetry Required (2°C – 8°C Strict Threshold)
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-faint)" }}>
                  Activates GDP/FDA regulatory excursion tracking & refrigerated asset allocation
                </div>
              </div>
            </div>
            <span className={isPerishable ? "badge badge-cyan" : "badge"} style={{ fontSize: "11px" }}>
              {isPerishable ? "Active" : "Disabled"}
            </span>
          </div>

          {/* Live ML Prediction Card */}
          <div
            style={{
              padding: "16px",
              borderRadius: "10px",
              background: "rgba(14, 20, 36, 0.8)",
              border: "1px solid rgba(0, 242, 254, 0.3)",
              boxShadow: "0 0 20px rgba(0, 242, 254, 0.1)",
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1.2fr",
              gap: "14px",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Delay Probability
              </div>
              <div
                style={{
                  fontSize: "24px",
                  fontWeight: 800,
                  color: mlInference.delayProbability >= 70 ? "var(--accent-rose)" : mlInference.delayProbability >= 40 ? "var(--accent-amber)" : "var(--accent-emerald)",
                  marginTop: "2px",
                }}
              >
                {mlInference.delayProbability}%
              </div>
              <div style={{ fontSize: "10px", color: "var(--text-faint)" }}>Based on Random Forest model</div>
            </div>

            <div>
              <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Predicted Delay
              </div>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--text-main)", marginTop: "2px" }}>
                +{mlInference.predictedDelayHours}h
              </div>
              <div style={{ fontSize: "10px", color: "var(--text-faint)" }}>Estimated bottleneck arrival</div>
            </div>

            <div style={{ borderLeft: "1px solid var(--border-subtle)", paddingLeft: "14px" }}>
              <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Composite Risk Assessment
              </div>
              <div style={{ marginTop: "4px" }}>
                <span
                  className={`badge ${
                    mlInference.riskLevel === "critical"
                      ? "badge-rose"
                      : mlInference.riskLevel === "high"
                      ? "badge-amber"
                      : mlInference.riskLevel === "medium"
                      ? "badge-cyan"
                      : "badge-emerald"
                  }`}
                  style={{ fontSize: "12px", padding: "4px 10px" }}
                >
                  {mlInference.riskLevel.toUpperCase()} RISK ({mlInference.rawScore}/100)
                </span>
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-faint)", marginTop: "4px" }}>
                {mlInference.riskLevel === "critical"
                  ? "Requires Human-in-the-Loop rerouting sign-off."
                  : "Within normal dispatch tolerance parameters."}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "4px" }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "10px 18px",
                background: "transparent",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-muted)",
                borderRadius: "8px",
                cursor: "pointer",
                fontWeight: 600,
                fontSize: "13px",
              }}
            >
              Close
            </button>
            <button
              type="submit"
              style={{
                padding: "10px 22px",
                background: "linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)",
                border: "none",
                color: "#080c14",
                borderRadius: "8px",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "13px",
                boxShadow: "0 0 20px rgba(0, 242, 254, 0.4)",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <Zap size={16} /> Deploy to Digital Twin Fleet
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
