"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  Clock,
  Filter,
  History,
  Lock,
  Search,
  ShieldCheck,
  User,
} from "lucide-react";
import { DecisionAudit } from "../lib/types";

interface AuditLogTableProps {
  logs: DecisionAudit[];
}

export default function AuditLogTable({ logs }: AuditLogTableProps) {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [selectedLog, setSelectedLog] = useState<DecisionAudit | null>(null);

  const filteredLogs = logs.filter(
    (l) =>
      l.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.actor.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.entity_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.reasoning && l.reasoning.toLowerCase().includes(searchTerm.toLowerCase()))
  );

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
              background: "rgba(16, 185, 129, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--accent-emerald)",
            }}
          >
            <Lock size={20} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h2 style={{ fontSize: "16px", fontWeight: 700 }}>
                Regulatory DecisionAudit & Governance Ledger
              </h2>
              <span className="badge badge-emerald">Tamper-Proof</span>
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              Chronological, immutable compliance log recording all human & AI autonomous operational actions
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", width: "260px" }}>
          <div
            style={{
              position: "relative",
              width: "100%",
              display: "flex",
              alignItems: "center",
            }}
          >
            <Search size={14} style={{ position: "absolute", left: "10px", color: "var(--text-muted)" }} />
            <input
              type="text"
              placeholder="Search audit trail..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px 8px 32px",
                borderRadius: "8px",
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid var(--border-subtle)",
                color: "#fff",
                fontSize: "12px",
                outline: "none",
              }}
            />
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="glass-panel" style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "12px" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border-subtle)", background: "rgba(0,0,0,0.2)" }}>
              <th style={{ padding: "12px 16px", color: "var(--text-muted)", fontWeight: 600 }}>TIMESTAMP</th>
              <th style={{ padding: "12px 16px", color: "var(--text-muted)", fontWeight: 600 }}>ACTION</th>
              <th style={{ padding: "12px 16px", color: "var(--text-muted)", fontWeight: 600 }}>ACTOR</th>
              <th style={{ padding: "12px 16px", color: "var(--text-muted)", fontWeight: 600 }}>ENTITY</th>
              <th style={{ padding: "12px 16px", color: "var(--text-muted)", fontWeight: 600 }}>RATIONALE</th>
              <th style={{ padding: "12px 16px", color: "var(--text-muted)", fontWeight: 600, textAlign: "right" }}>DIFF</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.map((log) => {
              const isApproved = log.action.includes("approved");
              return (
                <tr
                  key={log.id}
                  style={{
                    borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <td style={{ padding: "12px 16px", color: "var(--text-faint)", whiteSpace: "nowrap" }}>
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <span
                      className={`badge badge-${isApproved ? "emerald" : "cyan"}`}
                      style={{ fontSize: "10px" }}
                    >
                      {log.action.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px", fontWeight: 600, color: "#fff" }}>
                    {log.actor}
                    <span style={{ display: "block", fontSize: "10px", color: "var(--text-faint)", fontWeight: 400 }}>
                      Type: {log.actor_type}
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px", color: "var(--text-muted)" }}>
                    {log.entity_type} ({log.entity_id.slice(0, 8)}...)
                  </td>
                  <td style={{ padding: "12px 16px", color: "#cbd5e1", maxWidth: "320px" }}>
                    {log.reasoning || "System automated transition"}
                  </td>
                  <td style={{ padding: "12px 16px", textAlign: "right" }}>
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="btn-secondary"
                      style={{ padding: "4px 8px", fontSize: "11px" }}
                    >
                      Inspect State
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* State Diff Modal */}
      {selectedLog && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.8)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: "20px",
          }}
        >
          <div
            className="glass-panel"
            style={{
              width: "100%",
              maxWidth: "560px",
              padding: "24px",
              background: "#0c1322",
              border: "1px solid var(--accent-cyan)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 700 }}>
                Audit State Diff: {selectedLog.action}
              </h3>
              <button
                onClick={() => setSelectedLog(null)}
                className="btn-secondary"
                style={{ padding: "4px 8px" }}
              >
                Close
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "16px" }}>
              <div>
                <span style={{ fontSize: "11px", color: "var(--accent-rose)", fontWeight: 600 }}>
                  PREVIOUS STATE:
                </span>
                <pre
                  style={{
                    background: "rgba(0,0,0,0.4)",
                    padding: "10px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    color: "#94a3b8",
                    marginTop: "6px",
                    overflowX: "auto",
                  }}
                >
                  {JSON.stringify(selectedLog.previous_state || { status: "pending" }, null, 2)}
                </pre>
              </div>

              <div>
                <span style={{ fontSize: "11px", color: "var(--accent-emerald)", fontWeight: 600 }}>
                  NEW COMMITTED STATE:
                </span>
                <pre
                  style={{
                    background: "rgba(0,0,0,0.4)",
                    padding: "10px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    color: "#00f2fe",
                    marginTop: "6px",
                    overflowX: "auto",
                  }}
                >
                  {JSON.stringify(selectedLog.new_state || { status: "approved" }, null, 2)}
                </pre>
              </div>
            </div>

            <div style={{ fontSize: "11px", color: "var(--text-faint)" }}>
              Recorded by {selectedLog.actor} at {new Date(selectedLog.timestamp).toISOString()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
