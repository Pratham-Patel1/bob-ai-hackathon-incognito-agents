"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle,
  Clock,
  DollarSign,
  HelpCircle,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  UserCheck,
  X,
} from "lucide-react";
import { Recommendation } from "../lib/types";
import { approveRecommendationApi, rejectRecommendationApi } from "../lib/api";

interface RecommendationsPanelProps {
  recommendations: Recommendation[];
  onRecommendationUpdated?: () => void;
}

export default function RecommendationsPanel({
  recommendations,
  onRecommendationUpdated,
}: RecommendationsPanelProps) {
  const [activeRecs, setActiveRecs] = useState<Recommendation[]>(recommendations);
  const [selectedRec, setSelectedRec] = useState<Recommendation | null>(null);
  const [modalAction, setModalAction] = useState<"approve" | "reject" | null>(null);
  const [actorName, setActorName] = useState<string>("Operations Dispatcher 01");
  const [decisionNotes, setDecisionNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Sync state if props change
  React.useEffect(() => {
    setActiveRecs(recommendations);
  }, [recommendations]);

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
              background: "rgba(139, 92, 246, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--accent-purple)",
            }}
          >
            <ShieldCheck size={20} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h2 style={{ fontSize: "16px", fontWeight: 700 }}>
                AI Recommendation Engine & Human-in-the-Loop Governance
              </h2>
              <span className="badge badge-purple">Decision Gate</span>
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              Multi-objective intelligence synthesizing optimal corridors with mandatory human oversight
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

      {/* Recommendations Feed */}
      <div style={{ display: "grid", gap: "14px" }}>
        {activeRecs.map((rec) => {
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
                        ${rec.estimated_savings_usd.toLocaleString()}
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
                    {rec.reasoning_factors.map((factor, idx) => (
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
                        ✓ {factor}
                      </span>
                    ))}
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
