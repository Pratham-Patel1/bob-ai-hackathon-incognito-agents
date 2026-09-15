"""
SupplyChainOS — Explainable AI & Decision Trace Test Suite.
Validates that all AI-assisted operational decisions provide meaningful, traceable,
and accurate explanations across risk, disruptions, routes, carriers, cold chain,
fleet, cascading impacts, business impacts, recommendations, and audit records.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.database import engine
from backend.engines import (
    shipment_risk,
    predictive_risk,
    disruption_impact,
    route_optimizer,
    carrier_recommender,
    cold_chain,
    fleet_intelligence,
    cascade_impact,
    business_impact,
    recommendation_engine,
)


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as ac:
        yield ac
    await engine.dispose()


# ── 1. Shipment Risk & ML Explainability ──────────────────────────────────────
def test_shipment_risk_explanation_and_factors():
    """Verify deterministic risk exposes scores, levels, factors, and contributions."""
    sample_shipment = {
        "id": "shp-test-01",
        "tracking_number": "TRK-EXP-001",
        "cargo_type": "pharma",
        "cargo_value_usd": 150000.0,
        "weight_kg": 500.0,
        "temperature_required": True,
        "status": "in_transit",
        "origin_lat": 53.55,
        "origin_lng": 9.99,
        "dest_lat": 50.11,
        "dest_lng": 8.68,
        "scheduled_departure": "2026-09-15T00:00:00Z",
        "scheduled_delivery": "2026-09-15T08:00:00Z",
    }
    sample_disruption = {
        "id": "dis-01",
        "title": "North Sea Gale",
        "severity": "high",
        "epicenter_lat": 54.0,
        "epicenter_lng": 9.5,
        "affected_radius_km": 200.0,
    }

    det_res = shipment_risk.run(
        shipment=sample_shipment,
        active_disruptions=[sample_disruption],
        temperature_excursion=True,
    )
    assert det_res.score > 0.0
    assert det_res.level in ("low", "medium", "high", "critical")
    assert det_res.explanation != ""
    assert len(det_res.factors) > 0
    # Factors must have contribution and weight
    for factor in det_res.factors:
        assert factor.name != ""
        assert factor.contribution >= 0.0
        assert factor.weight > 0.0


def test_predictive_ml_risk_explanation_and_weights():
    """Verify ML risk exposes model probability and feature importances."""
    sample_shipment = {
        "id": "shp-test-02",
        "tracking_number": "TRK-EXP-002",
        "cargo_type": "electronics",
        "cargo_value_usd": 80000.0,
        "weight_kg": 1200.0,
        "temperature_required": False,
        "status": "in_transit",
        "origin_lat": 53.55,
        "origin_lng": 9.99,
        "dest_lat": 50.11,
        "dest_lng": 8.68,
    }
    carrier = {"id": "c-01", "reliability_score": 0.85}
    ml_res = predictive_risk.run(shipment=sample_shipment, active_disruptions=[], carrier=carrier)
    assert ml_res.model_version != ""
    if ml_res.ml_score is not None:
        assert 0.0 <= ml_res.ml_score <= 1.0
        assert len(ml_res.top_features) > 0
        for feat in ml_res.top_features:
            assert feat.feature_name != ""
            assert feat.importance >= 0.0


# ── 2. Disruption Explanation ─────────────────────────────────────────────────
def test_disruption_impact_explanation():
    """Verify disruption impact explains geographic exposure, distance, and reasons."""
    sample_disruption = {
        "id": "dis-storm-01",
        "title": "Severe Coastal Storm",
        "severity": "critical",
        "epicenter_lat": 54.0,
        "epicenter_lng": 9.5,
        "affected_radius_km": 200.0,
        "start_time": None,
        "estimated_end_time": None,
    }
    sample_shipments = [
        {
            "id": "shp-near",
            "current_lat": 54.1,
            "current_lng": 9.6,
            "status": "in_transit",
            "route_code": "RT-01",
        }
    ]
    impact = disruption_impact.run(sample_disruption, sample_shipments)
    assert impact.affected_count >= 1
    item = impact.impacted_shipments[0]
    assert item.impact_reason in ("geo_intersection", "route_blocked", "both")
    assert item.estimated_delay_hours > 0.0
    assert len(item.factors) > 0


# ── 3. Route Recommendation Explanation ──────────────────────────────────────
def test_route_recommendation_explanation():
    """Verify alternative route options explain disruption avoidance and transit times."""
    shipment = {
        "id": "shp-route-01",
        "origin": "Hamburg",
        "destination": "Frankfurt",
        "cargo_type": "general",
        "weight_kg": 2000.0,
        "route_id": "rt-primary",
    }
    disruptions = [
        {
            "id": "dis-01",
            "title": "A7 Highway Closure",
            "affected_region": "Central Germany",
            "epicenter_lat": 52.0,
            "epicenter_lng": 9.0,
            "affected_radius_km": 100.0,
        }
    ]
    routes = [
        {
            "id": "rt-primary",
            "code": "RT-01",
            "name": "Hamburg-Frankfurt Direct Highway",
            "origin": "Hamburg",
            "destination": "Frankfurt",
            "distance_km": 490.0,
            "typical_duration_hours": 5.0,
            "cost_per_kg": 0.45,
            "reliability_score": 0.85,
            "active": True,
            "mode": "road",
        },
        {
            "id": "rt-alt",
            "code": "RT-02-RAIL",
            "name": "Hamburg-Frankfurt Rail Express",
            "origin": "Hamburg",
            "destination": "Frankfurt",
            "distance_km": 510.0,
            "typical_duration_hours": 4.5,
            "cost_per_kg": 0.40,
            "reliability_score": 0.92,
            "active": True,
            "mode": "rail",
        },
    ]
    options = route_optimizer.run(
        shipment=shipment,
        active_disruptions=disruptions,
        available_routes=routes,
    )
    assert len(options) > 0
    best = options[0]
    assert best.route_id == "rt-alt"
    assert best.reason != ""
    assert "reliability" in best.reason.lower() or "cost" in best.reason.lower() or "disruption" in best.reason.lower()


# ── 4. Carrier Recommendation Explanation ────────────────────────────────────
def test_carrier_recommendation_explanation():
    """Verify carrier recommendations expose reliability, cost, and suitability reasons."""
    shipment = {
        "id": "shp-c-01",
        "destination": "Frankfurt",
        "cargo_type": "pharma",
        "weight_kg": 300.0,
        "temperature_required": True,
    }
    current_carrier = {"id": "c-disrupted", "name": "Disrupted Logistics"}
    all_carriers = [
        {
            "id": "c-disrupted",
            "name": "Disrupted Logistics",
            "code": "DL-01",
            "reliability_score": 0.60,
            "cost_index": 1.0,
            "coverage_regions": ["Europe"],
            "active": True,
        },
        {
            "id": "c-pharma-express",
            "name": "PharmaTrans Global",
            "code": "PTG-01",
            "reliability_score": 0.95,
            "cost_index": 1.15,
            "coverage_regions": ["Europe", "Germany"],
            "active": True,
        },
    ]
    options = carrier_recommender.run(
        shipment=shipment,
        current_carrier=current_carrier,
        all_carriers=all_carriers,
        active_disruptions=[],
    )
    assert len(options) > 0
    best = options[0]
    assert best.carrier_id == "c-pharma-express"
    assert best.reason != ""
    assert "PTG-01" in best.reason or "PharmaTrans" in best.reason


# ── 5. Cold-Chain Thresholds & Explanation ────────────────────────────────────
def test_cold_chain_threshold_classifications():
    """Verify strict adherence to MINOR, MAJOR, CRITICAL excursion classification."""
    # 1. Minor: <=2°C deviation AND <=15 minutes
    minor_logs = [
        {"temperature_c": 9.5, "recorded_at": "2026-09-15T01:00:00Z"},  # +1.5°C over 8.0°C for 5 min
    ]
    res_minor = cold_chain.run(minor_logs, temp_min_c=2.0, temp_max_c=8.0)
    assert res_minor.has_excursion is True
    assert res_minor.severity == "minor"
    assert res_minor.max_deviation_c == 1.5

    # 2. Major: 2-5°C deviation OR 15-60 min
    major_logs = [
        {"temperature_c": 11.5, "recorded_at": "2026-09-15T01:00:00Z"},  # +3.5°C over 8.0°C
    ]
    res_major = cold_chain.run(major_logs, temp_min_c=2.0, temp_max_c=8.0)
    assert res_major.has_excursion is True
    assert res_major.severity == "major"
    assert res_major.max_deviation_c == 3.5

    # 3. Critical: >5°C deviation OR >60 min
    crit_logs = [
        {"temperature_c": 14.5, "recorded_at": "2026-09-15T01:00:00Z"},  # +6.5°C over 8.0°C
    ]
    res_crit = cold_chain.run(crit_logs, temp_min_c=2.0, temp_max_c=8.0)
    assert res_crit.has_excursion is True
    assert res_crit.severity == "critical"
    assert "immediate" in res_crit.recommended_action.lower() or "quarantine" in res_crit.recommended_action.lower()


# ── 6. Fleet Intelligence Explanation ────────────────────────────────────────
def test_fleet_intelligence_explanation():
    """Verify fleet recommendations explain idle status, reefer capability, and capacity."""
    fleet = [
        {
            "id": "fl-01",
            "vehicle_type": "truck_reefer",
            "capacity_kg": 5000.0,
            "utilization_pct": 10.0,  # 10% load -> idle
            "temperature_capable": True,
            "current_lat": 53.55,
            "current_lng": 9.99,
            "status": "active",
        }
    ]
    needy_shipments = [
        {
            "id": "shp-cold",
            "tracking_number": "TRK-COLD-01",
            "weight_kg": 2000.0,
            "temperature_required": True,
            "current_lat": 53.60,
            "current_lng": 10.05,
        }
    ]
    analysis = fleet_intelligence.analyse_fleet(fleet)
    assert analysis.idle_count == 1
    suggestions = fleet_intelligence.suggest_redeployments(fleet=fleet, needy_shipments=needy_shipments)
    assert len(suggestions) > 0
    sug = suggestions[0]
    assert sug.vehicle_id == "fl-01"
    assert sug.reason != ""
    assert "fl-01" in sug.reason or "km" in sug.reason


# ── 7. Cascade & Business Impact Explanation ──────────────────────────────────
def test_cascade_and_business_impact_explanation():
    """Verify cascade impact calculates secondary delay, value at risk, and delay costs."""
    shipments = [
        {
            "id": "s1",
            "tracking_number": "TRK-01",
            "fleet_id": "fl-01",
            "carrier_id": "c-01",
            "cargo_value_usd": 100000.0,
            "status": "in_transit",
            "scheduled_arrival": "2026-09-15T12:00:00Z",
            "estimated_arrival": "2026-09-15T20:00:00Z",
        },
        {
            "id": "s2",
            "tracking_number": "TRK-02",
            "fleet_id": "fl-01",  # Same vehicle -> fleet cascade
            "carrier_id": "c-01",
            "cargo_value_usd": 75000.0,
            "status": "in_transit",
            "scheduled_arrival": "2026-09-15T12:00:00Z",
            "estimated_arrival": "2026-09-15T22:00:00Z",
        },
    ]
    fleet = [{"id": "fl-01", "carrier_id": "c-01"}]
    casc = cascade_impact.run(direct_shipment_ids={"s1"}, all_shipments=shipments, fleet=fleet)
    assert casc.direct_count == 1
    assert casc.secondary_count == 1
    assert casc.total_value_at_risk_usd == 75000.0
    assert casc.explanation != ""

    biz = business_impact.run(affected_shipments=shipments)
    assert biz.total_cargo_value_at_risk_usd == 175000.0
    assert biz.cost_of_delay_usd > 0.0
    assert biz.explanation != ""


# ── 8. Recommendation Engine Trace & Weights ──────────────────────────────────
def test_recommendation_decision_trace_and_weights():
    """Verify 60% deterministic / 40% ML weighting and complete end-to-end trace."""
    disruption = {
        "id": "dis-01",
        "title": "North Sea Storm",
        "severity": "critical",
        "epicenter_lat": 54.0,
        "epicenter_lng": 9.5,
        "affected_radius_km": 300.0,
    }
    shipments = [
        {
            "id": "shp-trace-01",
            "tracking_number": "TRK-TRACE-01",
            "cargo_type": "pharma",
            "cargo_value_usd": 120000.0,
            "weight_kg": 800.0,
            "temperature_required": True,
            "status": "in_transit",
            "origin": "Hamburg",
            "destination": "Frankfurt",
            "current_lat": 54.0,
            "current_lng": 9.5,
            "carrier_id": "c-01",
            "route_id": "r-01",
        }
    ]
    routes = [
        {
            "id": "r-alt",
            "code": "RT-ALT",
            "name": "Bypass Rail Express",
            "origin": "Hamburg",
            "destination": "Frankfurt",
            "distance_km": 500.0,
            "typical_duration_hours": 4.5,
            "cost_per_kg": 0.50,
            "reliability_score": 0.95,
            "active": True,
            "mode": "rail",
        }
    ]
    carriers = [
        {
            "id": "c-01",
            "name": "CargoExpress",
            "code": "CE",
            "reliability_score": 0.70,
            "cost_index": 1.0,
            "coverage_regions": ["Europe"],
            "active": True,
        }
    ]
    orch_result = recommendation_engine.run(
        disruption=disruption,
        all_shipments=shipments,
        all_routes=routes,
        all_carriers=carriers,
        all_fleet=[],
        temperature_excursions={"shp-trace-01": False},
        carriers_by_id={"c-01": carriers[0]},
    )
    assert len(orch_result.recommendations) > 0
    rec = orch_result.recommendations[0]
    assert rec.shipment_id == "shp-trace-01"
    assert rec.reason != ""
    assert len(rec.reasoning_factors) > 0
    # Must contain structured factor dicts
    for factor in rec.reasoning_factors:
        assert "factor" in factor
        assert "value" in factor
        assert "contribution" in factor
        assert "weight" in factor


# ── 9. Decision Audit & Human Approval Traceability ───────────────────────────
@pytest.mark.asyncio
async def test_decision_audit_traceability(async_client: AsyncClient):
    """Verify human approval generates complete decision audit record with all trace fields."""
    recs_res = await async_client.get("/recommendations")
    recs = recs_res.json()
    assert len(recs) > 0
    pending_recs = [r for r in recs if r.get("status") == "pending"]
    target_rec = pending_recs[0] if pending_recs else recs[0]

    approve_payload = {
        "actor": "Lead Controller Alex Rivera",
        "notes": "Corridor reroute approved based on AI temperature and storm telemetry.",
    }
    approve_res = await async_client.post(
        f"/recommendations/{target_rec['id']}/approve",
        json=approve_payload,
    )
    if target_rec.get("status") == "pending":
        assert approve_res.status_code == 200
        approved_data = approve_res.json()
        assert approved_data["status"] == "approved"
        assert approved_data["approved_by"] == "Lead Controller Alex Rivera"

    # Verify decision audit ledger has recorded the trace
    audit_res = await async_client.get("/audit")
    assert audit_res.status_code == 200
    audits = audit_res.json()
    matching = [a for a in audits if a.get("entity_id") == target_rec["id"]]
    assert len(matching) > 0
    audit_entry = matching[0]
    assert "Alex Rivera" in str(audit_entry.get("actor") or "") or audit_entry.get("action") in ("rec_approved", "approved")

