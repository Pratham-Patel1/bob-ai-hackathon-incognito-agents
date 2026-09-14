"use client";

import React, { useState } from "react";
import { AlertTriangle, Flame, ShieldAlert, Sliders, X, Zap } from "lucide-react";
import { Disruption } from "../lib/types";

interface InjectDisruptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInjectDisruption: (disruption: Disruption) => void;
}

const PRESETS = [
  {
    title: "Rotterdam Port Stevedore Strike",
    type: "port_congestion",
    severity: "critical" as const,
    latitude: 51.92,
    longitude: 4.48,
    radius: 140,
    delay: 20,
    description: "Union walkout blocking automated gantry cranes and deep-water container terminal operations.",
  },
  {
    title: "Brenner Pass Blizzard & Snowstorm",
    type: "severe_weather",
    severity: "critical" as const,
    latitude: 47.0,
    longitude: 11.5,
    radius: 175,
    delay: 24,
    description: "Heavy snow accumulation and sub-zero blizzard shutting Alpine freight passes between Austria and Italy.",
  },
  {
    title: "Rhine Gorge Low-Water Barge Halt",
    type: "infrastructure",
    severity: "high" as const,
    latitude: 50.15,
    longitude: 7.72,
    radius: 95,
    delay: 12,
    description: "Water levels at Kaub gauge dropping below safe draft limits, forcing barge traffic diversion onto road carriers.",
  },
  {
    title: "Antwerp Chemical Corridor Hazmat Hazard",
    type: "infrastructure",
    severity: "high" as const,
    latitude: 51.26,
    longitude: 4.35,
    radius: 70,
    delay: 8,
    description: "Emergency hazmat containment perimeter restricting industrial motorway access lanes.",
  },
];

export default function InjectDisruptionModal({
  isOpen,
  onClose,
  onInjectDisruption,
}: InjectDisruptionModalProps) {
  const [selectedPresetIndex, setSelectedPresetIndex] = useState<number>(0);
  const [customTitle, setCustomTitle] = useState<string>(PRESETS[0].title);
  const [severity, setSeverity] = useState<"low" | "medium" | "high" | "critical">(PRESETS[0].severity);
  const [radiusKm, setRadiusKm] = useState<number>(PRESETS[0].radius);
  const [delayHours, setDelayHours] = useState<number>(PRESETS[0].delay);
  const [description, setDescription] = useState<string>(PRESETS[0].description);
  const [lat, setLat] = useState<number>(PRESETS[0].latitude);
  const [lng, setLng] = useState<number>(PRESETS[0].longitude);

  if (!isOpen) return null;

  const handleSelectPreset = (idx: number) => {
    setSelectedPresetIndex(idx);
    const p = PRESETS[idx];
    setCustomTitle(p.title);
    setSeverity(p.severity);
    setRadiusKm(p.radius);
    setDelayHours(p.delay);
    setDescription(p.description);
    setLat(p.latitude);
    setLng(p.longitude);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newDisruption: Disruption = {
      id: `d-${Date.now().toString().slice(-4)}`,
      title: customTitle,
      type: PRESETS[selectedPresetIndex]?.type || "severe_weather",
      severity,
      latitude: lat,
      longitude: lng,
      affected_radius_km: radiusKm,
      status: "active",
      description,
      estimated_delay_hours: delayHours,
      reported_at: new Date().toISOString(),
    };

    onInjectDisruption(newDisruption);
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
          maxWidth: "640px",
          background: "linear-gradient(180deg, rgba(20, 27, 45, 0.95) 0%, rgba(10, 15, 29, 0.98) 100%)",
          border: "1px solid rgba(244, 63, 94, 0.35)",
          boxShadow: "0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(244, 63, 94, 0.2)",
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
                background: "rgba(244, 63, 94, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--accent-rose)",
              }}
            >
              <Flame size={22} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h2 style={{ fontSize: "17px", fontWeight: 700 }}>Disruption Chaos Generator</h2>
                <span className="badge badge-rose">Live Injection</span>
              </div>
              <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Simulate a real-time event to evaluate blast-radius collision and AI autonomous response
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

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Preset Buttons */}
          <div>
            <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "8px" }}>
              SELECT DISRUPTION SCENARIO PRESET:
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
              {PRESETS.map((p, idx) => (
                <button
                  type="button"
                  key={p.title}
                  onClick={() => handleSelectPreset(idx)}
                  style={{
                    padding: "10px 12px",
                    textAlign: "left",
                    borderRadius: "8px",
                    background: selectedPresetIndex === idx ? "rgba(244, 63, 94, 0.18)" : "rgba(255, 255, 255, 0.03)",
                    border: selectedPresetIndex === idx ? "1px solid var(--accent-rose)" : "1px solid var(--border-subtle)",
                    color: selectedPresetIndex === idx ? "#fff" : "var(--text-muted)",
                    cursor: "pointer",
                    fontSize: "12px",
                    fontWeight: 600,
                    transition: "all 0.15s ease",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span>{p.title}</span>
                    <span className={p.severity === "critical" ? "badge badge-rose" : "badge badge-amber"} style={{ fontSize: "9px" }}>
                      {p.severity}
                    </span>
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-faint)" }}>
                    Radius: {p.radius}km • +{p.delay}h delay
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Title & Description */}
          <div>
            <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
              Event Title
            </label>
            <input
              type="text"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "10px 12px",
                background: "rgba(8, 12, 20, 0.8)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "8px",
                color: "#fff",
                fontSize: "13px",
              }}
            />
          </div>

          {/* Sliders Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            {/* Blast Radius Slider */}
            <div style={{ background: "rgba(8, 12, 20, 0.5)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Geospatial Blast Radius</span>
                <strong style={{ color: "var(--accent-rose)", fontSize: "13px" }}>{radiusKm} km</strong>
              </div>
              <input
                type="range"
                min={30}
                max={350}
                step={10}
                value={radiusKm}
                onChange={(e) => setRadiusKm(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--accent-rose)", cursor: "pointer" }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--text-faint)", marginTop: "4px" }}>
                <span>30 km (Local)</span>
                <span>350 km (Regional)</span>
              </div>
            </div>

            {/* Delay Slider */}
            <div style={{ background: "rgba(8, 12, 20, 0.5)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>Estimated Bottleneck Delay</span>
                <strong style={{ color: "var(--accent-amber)", fontSize: "13px" }}>+{delayHours} hours</strong>
              </div>
              <input
                type="range"
                min={2}
                max={48}
                step={2}
                value={delayHours}
                onChange={(e) => setDelayHours(Number(e.target.value))}
                style={{ width: "100%", accentColor: "var(--accent-amber)", cursor: "pointer" }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--text-faint)", marginTop: "4px" }}>
                <span>+2h (Minor)</span>
                <span>+48h (Severe)</span>
              </div>
            </div>
          </div>

          {/* Severity Badges */}
          <div>
            <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "8px" }}>
              SEVERITY LEVEL:
            </label>
            <div style={{ display: "flex", gap: "10px" }}>
              {(["low", "medium", "high", "critical"] as const).map((lvl) => (
                <button
                  type="button"
                  key={lvl}
                  onClick={() => setSeverity(lvl)}
                  style={{
                    flex: 1,
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: severity === lvl ? "1px solid var(--accent-rose)" : "1px solid var(--border-subtle)",
                    background: severity === lvl ? "rgba(244, 63, 94, 0.2)" : "rgba(255, 255, 255, 0.02)",
                    color: severity === lvl ? "#fff" : "var(--text-muted)",
                    fontWeight: 700,
                    fontSize: "11px",
                    cursor: "pointer",
                    textTransform: "uppercase",
                  }}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          {/* System Response Info */}
          <div
            style={{
              padding: "12px",
              borderRadius: "8px",
              background: "rgba(0, 242, 254, 0.05)",
              border: "1px solid rgba(0, 242, 254, 0.2)",
              fontSize: "12px",
              color: "var(--text-muted)",
              lineHeight: 1.5,
            }}
          >
            ⚡ <strong style={{ color: "var(--accent-cyan)" }}>Autonomous Orchestration Pipeline:</strong> Injecting this disruption will immediately project the blast radius onto the Digital Twin map, detect all intersecting freight lanes, and generate real-time alternative routes or carrier swaps.
          </div>

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "8px" }}>
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
              Cancel
            </button>
            <button
              type="submit"
              style={{
                padding: "10px 22px",
                background: "linear-gradient(135deg, #f43f5e 0%, #e11d48 100%)",
                border: "none",
                color: "#fff",
                borderRadius: "8px",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "13px",
                boxShadow: "0 0 20px rgba(244, 63, 94, 0.4)",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <Zap size={16} /> Inject Threat & Re-Score
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
