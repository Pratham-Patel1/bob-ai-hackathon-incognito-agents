"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Check,
  CheckCircle,
  Clock,
  Cpu,
  DollarSign,
  HelpCircle,
  RotateCcw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  TrendingDown,
  UserCheck,
  X,
  Zap,
} from "lucide-react";
import { Recommendation } from "../lib/types";
import {
  approveRecommendationApi,
  rejectRecommendationApi,
  formatCurrency,
  queryCopilotApi,
  CopilotResponse,
} from "../lib/api";

interface RecommendationsPanelProps {
  recommendations: Recommendation[];
  filterId?: string;
  excludeId?: string;
  hideHeader?: boolean;
  noMargin?: boolean;
  onRecommendationUpdated?: () => void;
}

export default function RecommendationsPanel({
  recommendations,
  filterId,
  excludeId,
  hideHeader = false,
  noMargin = false,
  onRecommendationUpdated,
}: RecommendationsPanelProps) {
  const [activeRecs, setActiveRecs] = useState<Recommendation[]>(recommendations);
  const [selectedRec, setSelectedRec] = useState<Recommendation | null>(null);
  const [modalAction, setModalAction] = useState<"approve" | "reject" | null>(null);
  const [actorName, setActorName] = useState<string>("Operations Dispatcher 01");
  const [decisionNotes, setDecisionNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // AI Copilot State
  const [copilotPrompt, setCopilotPrompt] = useState<string>("");
  const [copilotLoading, setCopilotLoading] = useState<boolean>(false);
  const [copilotResponse, setCopilotResponse] = useState<CopilotResponse | null>(null);

  // Sync state if props change
  React.useEffect(() => {
    setActiveRecs(recommendations);
  }, [recommendations]);

  const displayedRecs = activeRecs.filter((r) => {
    if (filterId) return r.id === filterId;
    if (excludeId) return r.id !== excludeId;
    return true;
  });

  const handleSendQuery = async (overridePrompt?: string) => {
    const text = overridePrompt || copilotPrompt;
    if (!text.trim()) return;
    setCopilotLoading(true);
    const res = await queryCopilotApi(text, { actor: actorName });
    setCopilotResponse(res);
    setCopilotLoading(false);
  };

  const handleOpenModal = (rec: Recommendation, action: "approve" | "reject") => {
    setSelectedRec(rec);
    setModalAction(action);
    setDecisionNotes(
      action === "approve"
        ? `Approved recommended action ${rec.type.toUpperCase()} based on AI simulation.`
        : `Rejected due to route constraints or cost threshold.`
    );
  };

  const handleSubmitDecision = async () => {
    if (!selectedRec || !modalAction) return;
    setIsSubmitting(true);

    if (modalAction === "approve") {
      await approveRecommendationApi(selectedRec.id, actorName, decisionNotes);
      setActiveRecs((prev) =>
        prev.map((r) =>
          r.id === selectedRec.id
            ? { ...r, status: "approved", approved_by: actorName, approved_at: new Date().toISOString() }
            : r
        )
      );
    } else {
      await rejectRecommendationApi(selectedRec.id, actorName, decisionNotes);
      setActiveRecs((prev) =>
        prev.map((r) =>
          r.id === selectedRec.id
            ? { ...r, status: "rejected", approved_by: actorName, approved_at: new Date().toISOString() }
            : r
        )
      );
    }

    setIsSubmitting(false);
    setModalAction(null);
    setSelectedRec(null);
    if (onRecommendationUpdated) onRecommendationUpdated();
  };

  const PRESET_QUERIES = [
    "Which shipments are affected by the active storm?",
    "What is the risk of shipment TRK-PHARMA-2026-001?",
    "Which alternative routes are available?",
    "Are there cold-chain temperature excursions?",
    "Which fleet vehicles are idle?",
    "What is the cascade impact of this disruption?",
    "Simulate what happens if this disruption affects route RT-01",
    "Approve recommendation without credentials",
  ];

  return (
    <div style={{ margin: noMargin ? "0" : "0 20px 20px 20px" }}>
      {/* 1. Header Banner & Interactive AI Copilot Workspace */}
      {!hideHeader && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "20px" }}>
          <div
            className="glass-panel"
            style={{
              padding: "16px 20px",
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
                  background: "linear-gradient(135deg, rgba(139, 92, 246, 0.3) 0%, rgba(0, 242, 254, 0.3) 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--accent-cyan)",
                  boxShadow: "0 0 12px rgba(0, 242, 254, 0.2)",
                }}
              >
                <Bot size={22} />
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <h2 style={{ fontSize: "16px", fontWeight: 700 }}>
                    IBM Bob Copilot — Model Context Protocol (MCP) Interface
                  </h2>
                  <span className="badge badge-cyan">MCP JSON-RPC 2.0</span>
                  <span className="badge badge-purple">Human-in-the-Loop</span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Natural language operations gateway querying live telemetry, multi-factor risk engines, and governed state machines
                </p>
              </div>
            </div>

            <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
              <span className="badge badge-emerald">
                {activeRecs.filter((r) => r.status === "approved").length} Approved
              </span>
              <span className="badge badge-rose">
                {activeRecs.filter((r) => r.status === "pending").length} Pending Review
              </span>
            </div>
          </div>

          {/* Interactive Query Console */}
          <div className="glass-panel" style={{ padding: "20px", background: "rgba(10, 16, 30, 0.85)", border: "1px solid rgba(0, 242, 254, 0.25)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
              <Sparkles size={16} color="var(--accent-cyan)" />
              <span style={{ fontSize: "13px", fontWeight: 700, color: "#fff" }}>
                Conversational Copilot Operations Query
              </span>
            </div>

            {/* Quick Prompt Chips */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "14px" }}>
              {PRESET_QUERIES.map((pq, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setCopilotPrompt(pq);
                    handleSendQuery(pq);
                  }}
                  className="btn-secondary"
                  style={{
                    fontSize: "11px",
                    padding: "4px 10px",
                    borderRadius: "6px",
                    background: "rgba(255, 255, 255, 0.04)",
                    borderColor: "rgba(255, 255, 255, 0.08)",
                  }}
                >
                  {pq}
                </button>
              ))}
            </div>

            {/* Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendQuery();
              }}
              style={{ display: "flex", gap: "8px" }}
            >
              <input
                type="text"
                placeholder="Ask Bob Copilot e.g., 'What is the risk of shipment TRK-PHARMA-2026-001?' or 'Which alternative routes are available?'"
                value={copilotPrompt}
                onChange={(e) => setCopilotPrompt(e.target.value)}
                style={{
                  flex: 1,
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "rgba(0, 0, 0, 0.4)",
                  border: "1px solid var(--border-subtle)",
                  color: "#fff",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
              <button
                type="submit"
                disabled={copilotLoading}
                className="btn-primary"
                style={{ padding: "0 20px", display: "flex", alignItems: "center", gap: "6px" }}
              >
                <Send size={14} />
                <span>{copilotLoading ? "Invoking MCP..." : "Query Copilot"}</span>
              </button>
            </form>

            {/* Copilot Result Display */}
            {copilotResponse && (
              <div
                style={{
                  marginTop: "16px",
                  padding: "16px",
                  borderRadius: "10px",
                  background: copilotResponse.status === "approval_required"
                    ? "rgba(244, 63, 94, 0.08)"
                    : "rgba(0, 242, 254, 0.05)",
                  border: copilotResponse.status === "approval_required"
                    ? "1px solid rgba(244, 63, 94, 0.3)"
                    : "1px solid rgba(0, 242, 254, 0.25)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div
                      style={{
                        width: "22px",
                        height: "22px",
                        borderRadius: "6px",
                        background: "rgba(0, 242, 254, 0.15)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "var(--accent-cyan)",
                      }}
                    >
                      <Terminal size={12} />
                    </div>
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--accent-cyan)" }}>
                      MCP Tool Dispatched: <code style={{ color: "#fff" }}>{copilotResponse.tool_called}()</code>
                    </span>
                  </div>

                  <span className={`badge badge-${copilotResponse.status === "approval_required" ? "rose" : "emerald"}`} style={{ fontSize: "10px" }}>
                    {copilotResponse.status === "approval_required" ? "HUMAN SIGN-OFF REQUIRED" : "EXECUTION SUCCESS"}
                  </span>
                </div>

                <div
                  style={{
                    fontSize: "13px",
                    color: "#e2e8f0",
                    lineHeight: "1.6",
                    whiteSpace: "pre-line",
                    fontFamily: "Inter, sans-serif",
                  }}
                >
                  {copilotResponse.explanation}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. Candidate Recommendations & Decision Gate Feed */}
      <div style={{ display: "grid", gap: "14px" }}>
        {displayedRecs.map((rec) => {
          const isPending = rec.status === "pending";
          const isApproved = rec.status === "approved";
          const isCritical = rec.priority === "critical";

          return (
            <div
              key={rec.id}
              className="glass-panel"
              style={{
                padding: "20px",
                borderColor: isApproved
                  ? "rgba(16, 185, 129, 0.4)"
                  : isCritical
                  ? "rgba(244, 63, 94, 0.4)"
                  : "var(--border-subtle)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  flexWrap: "wrap",
                  gap: "12px",
                  marginBottom: "12px",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                    <span
                      className={`badge badge-${isCritical ? "rose" : "amber"}`}
                      style={{ fontSize: "10px" }}
                    >
                      {rec.priority.toUpperCase()} PRIORITY
                    </span>
                    <span className="badge badge-cyan" style={{ fontSize: "10px" }}>
                      ACTION: {rec.type.replace("_", " ").toUpperCase()}
                    </span>
                    <span
                      className={`badge badge-${isApproved ? "emerald" : isPending ? "purple" : "rose"}`}
                      style={{ fontSize: "10px" }}
                    >
                      STATUS: {rec.status.toUpperCase()}
                    </span>
                  </div>

                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#fff" }}>
                    {rec.title}
                  </h3>
                </div>

                {/* Savings & Delay Stats */}
                <div style={{ display: "flex", gap: "16px", textAlign: "right" }}>
                  {rec.estimated_savings_usd && (
                    <div>
                      <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--accent-emerald)" }}>
                        {formatCurrency(rec.estimated_savings_usd)}
                      </div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>SLA Savings</div>
                    </div>
                  )}
                  {rec.estimated_delay_reduction_hours && (
                    <div>
                      <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--accent-cyan)" }}>
                        -{rec.estimated_delay_reduction_hours}h
                      </div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Delay Reduced</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Description & Reason */}
              <p style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "12px", lineHeight: "1.5" }}>
                {rec.description || rec.reason}
              </p>

              {/* Explainable AI Reasoning Factors */}
              {rec.reasoning_factors && rec.reasoning_factors.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-faint)", marginBottom: "6px" }}>
                    EXPLAINABLE AI FACTORS:
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {rec.reasoning_factors.map((factor, idx) => {
                      const factorLabel =
                        typeof factor === "string"
                          ? factor
                          : factor.factor ||
                            factor.name ||
                            (typeof factor.value !== "undefined" ? `factor: ${factor.value}` : "Key Factor");
                      return (
                        <span
                          key={idx}
                          style={{
                            fontSize: "11px",
                            padding: "3px 10px",
                            borderRadius: "6px",
                            background: "rgba(255, 255, 255, 0.04)",
                            border: "1px solid rgba(255, 255, 255, 0.08)",
                            color: "#cbd5e1",
                          }}
                        >
                          ✓ {factorLabel}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Footer Actions / Sign-off State */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  paddingTop: "14px",
                  borderTop: "1px solid var(--border-subtle)",
                }}
              >
                {isApproved ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "var(--accent-emerald)" }}>
                    <CheckCircle size={16} />
                    <span>
                      Approved by <strong>{rec.approved_by || "IBM Bob Copilot"}</strong> • Logged to DecisionAudit
                    </span>
                  </div>
                ) : !isPending ? (
                  <div style={{ fontSize: "12px", color: "var(--accent-rose)" }}>
                    Rejected by {rec.approved_by || "Operations"}
                  </div>
                ) : (
                  <div style={{ fontSize: "11px", color: "var(--text-faint)" }}>
                    Requires Dispatcher or AI Officer Sign-Off (Threshold $50k)
                  </div>
                )}

                {isPending && (
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      onClick={() => handleOpenModal(rec, "reject")}
                      className="btn-secondary"
                      style={{ fontSize: "12px", padding: "6px 14px", color: "var(--accent-rose)" }}
                    >
                      <X size={14} />
                      <span>Reject</span>
                    </button>
                    <button
                      onClick={() => handleOpenModal(rec, "approve")}
                      className="btn-primary"
                      style={{ fontSize: "12px", padding: "6px 16px" }}
                    >
                      <Check size={14} />
                      <span>Approve Corridor</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Decision Modal */}
      {modalAction && selectedRec && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.75)",
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
              maxWidth: "480px",
              padding: "24px",
              background: "#0c1322",
              border: modalAction === "approve" ? "1px solid var(--accent-emerald)" : "1px solid var(--accent-rose)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <UserCheck size={20} color={modalAction === "approve" ? "var(--accent-emerald)" : "var(--accent-rose)"} />
                <h3 style={{ fontSize: "16px", fontWeight: 700 }}>
                  {modalAction === "approve" ? "Approve AI Recommendation" : "Reject Recommendation"}
                </h3>
              </div>
              <button
                onClick={() => setModalAction(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "16px" }}>
              Action for: <strong>{selectedRec.title}</strong>
            </div>

            <div style={{ display: "grid", gap: "12px", marginBottom: "20px" }}>
              <div>
                <label style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
                  Sign-Off Officer / Copilot Actor:
                </label>
                <input
                  type="text"
                  value={actorName}
                  onChange={(e) => setActorName(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.05)",
                    border: "1px solid var(--border-subtle)",
                    color: "#fff",
                    fontSize: "13px",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "var(--text-muted)", display: "block", marginBottom: "6px" }}>
                  Audit Justification Notes:
                </label>
                <textarea
                  rows={3}
                  value={decisionNotes}
                  onChange={(e) => setDecisionNotes(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.05)",
                    border: "1px solid var(--border-subtle)",
                    color: "#fff",
                    fontSize: "13px",
                    outline: "none",
                    fontFamily: "Inter, sans-serif",
                  }}
                />
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button onClick={() => setModalAction(null)} className="btn-secondary" disabled={isSubmitting}>
                Cancel
              </button>
              <button
                onClick={handleSubmitDecision}
                disabled={isSubmitting}
                className={modalAction === "approve" ? "btn-primary" : "btn-secondary"}
                style={{
                  background: modalAction === "reject" ? "var(--accent-rose)" : undefined,
                  color: modalAction === "reject" ? "#fff" : undefined,
                }}
              >
                {isSubmitting
                  ? "Submitting..."
                  : modalAction === "approve"
                  ? "Confirm & Log Approval"
                  : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
