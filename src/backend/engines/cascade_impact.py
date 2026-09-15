"""
CascadingImpactEngine — first-order cascading disruption impact analysis.

Pure Python — no FastAPI or SQLAlchemy imports.

Two cascade paths (depth 1):
  1. Fleet cascade: delayed vehicle → downstream shipments on same vehicle
  2. Carrier cascade: carrier capacity overloaded → at-risk shipments on same carrier
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CascadeNode:
    shipment_id: str
    tracking_number: str
    level: int                    # 1 = secondary
    impact_type: str              # fleet_cascade | carrier_cascade
    caused_by_shipment_id: str
    estimated_delay_hours: float


@dataclass
class CascadeAnalysis:
    direct_count: int
    secondary_count: int
    cascade_chain: list[CascadeNode] = field(default_factory=list)
    total_value_at_risk_usd: float = 0.0
    total_delay_hours_estimate: float = 0.0
    explanation: str = ""


def run(
    direct_shipment_ids: set[str],
    all_shipments: list[dict[str, Any]],
    fleet: list[dict[str, Any]],
) -> CascadeAnalysis:
    """
    Model first-order cascading impact.

    Args:
        direct_shipment_ids: set of shipment IDs directly affected by the disruption
        all_shipments: all shipment dicts with keys:
            id, tracking_number, fleet_id, carrier_id,
            cargo_value_usd, status, scheduled_departure
        fleet: list of fleet dicts with id, carrier_id

    Returns:
        CascadeAnalysis with secondary impact nodes.
    """
    secondary_ids: set[str] = set()
    cascade_nodes: list[CascadeNode] = []

    # Build lookup maps
    shipments_by_id: dict[str, dict] = {str(s["id"]): s for s in all_shipments}
    direct_shipments = [shipments_by_id[sid] for sid in direct_shipment_ids if sid in shipments_by_id]

    # ── Path 1: Fleet cascade ────────────────────────────────────────────────
    # For each directly-affected shipment that has a fleet_id:
    # All other in-transit shipments on the same vehicle are secondary.
    direct_fleet_ids: set[str] = {
        str(s["fleet_id"])
        for s in direct_shipments
        if s.get("fleet_id")
    }

    for shipment in all_shipments:
        sid = str(shipment["id"])
        if sid in direct_shipment_ids:
            continue

        fleet_id = shipment.get("fleet_id")
        if fleet_id and str(fleet_id) in direct_fleet_ids:
            status = shipment.get("status", "")
            if status in ("in_transit", "at_risk"):
                # Find which direct shipment caused this
                caused_by = next(
                    (
                        str(ds["id"])
                        for ds in direct_shipments
                        if str(ds.get("fleet_id") or "") == str(fleet_id)
                    ),
                    "",
                )
                if sid not in secondary_ids:
                    secondary_ids.add(sid)
                    cascade_nodes.append(
                        CascadeNode(
                            shipment_id=sid,
                            tracking_number=str(shipment.get("tracking_number") or sid),
                            level=1,
                            impact_type="fleet_cascade",
                            caused_by_shipment_id=caused_by,
                            estimated_delay_hours=12.0,  # conservative estimate
                        )
                    )

    # ── Path 2: Carrier cascade ──────────────────────────────────────────────
    # If a carrier has >30% of its active capacity in direct-impact shipments,
    # flag other shipments on that carrier as elevated risk.
    carrier_totals: dict[str, int] = {}
    carrier_direct: dict[str, int] = {}

    for shipment in all_shipments:
        cid = str(shipment.get("carrier_id") or "")
        if not cid:
            continue
        if shipment.get("status") in ("in_transit", "at_risk", "delayed"):
            carrier_totals[cid] = carrier_totals.get(cid, 0) + 1
            if str(shipment["id"]) in direct_shipment_ids:
                carrier_direct[cid] = carrier_direct.get(cid, 0) + 1

    overloaded_carriers: set[str] = {
        cid
        for cid, count in carrier_direct.items()
        if carrier_totals.get(cid, 1) > 0
        and count / carrier_totals[cid] > 0.30
    }

    for shipment in all_shipments:
        sid = str(shipment["id"])
        if sid in direct_shipment_ids or sid in secondary_ids:
            continue

        cid = str(shipment.get("carrier_id") or "")
        if cid in overloaded_carriers:
            status = shipment.get("status", "")
            if status in ("in_transit", "at_risk"):
                # Caused by whichever direct shipment on same carrier
                caused_by = next(
                    (
                        str(ds["id"])
                        for ds in direct_shipments
                        if str(ds.get("carrier_id") or "") == cid
                    ),
                    "",
                )
                secondary_ids.add(sid)
                cascade_nodes.append(
                    CascadeNode(
                        shipment_id=sid,
                        tracking_number=str(shipment.get("tracking_number") or sid),
                        level=1,
                        impact_type="carrier_cascade",
                        caused_by_shipment_id=caused_by,
                        estimated_delay_hours=6.0,
                    )
                )

    # Financial totals
    total_value = sum(
        float(shipments_by_id[nid].get("cargo_value_usd") or 0)
        for nid in secondary_ids
        if nid in shipments_by_id
    )
    total_delay = sum(n.estimated_delay_hours for n in cascade_nodes)

    direct_count = len(direct_shipment_ids)
    secondary_count = len(secondary_ids)

    explanation = (
        f"{direct_count} shipments directly affected. "
        f"{secondary_count} secondary shipments identified "
        f"({sum(1 for n in cascade_nodes if n.impact_type == 'fleet_cascade')} fleet cascade, "
        f"{sum(1 for n in cascade_nodes if n.impact_type == 'carrier_cascade')} carrier cascade). "
        f"Total secondary cargo value at risk: ${total_value:,.0f}."
    )

    return CascadeAnalysis(
        direct_count=direct_count,
        secondary_count=secondary_count,
        cascade_chain=cascade_nodes,
        total_value_at_risk_usd=round(total_value, 2),
        total_delay_hours_estimate=round(total_delay, 1),
        explanation=explanation,
    )
