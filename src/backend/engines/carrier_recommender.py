"""
CarrierRecommendationEngine — rank alternative carriers for a disrupted shipment.

Pure Python — no FastAPI or SQLAlchemy imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CarrierOption:
    carrier_id: str
    carrier_name: str
    carrier_code: str
    score: float
    reliability_score: float
    cost_index: float
    covers_region: bool
    reason: str


def run(
    shipment: dict[str, Any],
    current_carrier: dict[str, Any],
    all_carriers: list[dict[str, Any]],
    active_disruptions: list[dict[str, Any]],
    top_n: int = 3,
) -> list[CarrierOption]:
    """
    Rank alternative carriers for a shipment whose current carrier is disrupted.

    Args:
        shipment: dict with keys:
            cargo_type (str), weight_kg (float),
            temperature_required (bool), destination (str)
        current_carrier: dict with key id (str)
        all_carriers: list of carrier dicts with keys:
            id, name, code, type, reliability_score, cost_index,
            coverage_regions (list[str]), active (bool)
        active_disruptions: list of disruption dicts with affected_region (str)
        top_n: number of top carriers to return.

    Returns:
        List of CarrierOption sorted by score descending.
    """
    destination = (shipment.get("destination") or "").strip()
    temp_required = bool(shipment.get("temperature_required", False))
    current_carrier_id = str(current_carrier.get("id") or "")

    # Regions affected by active disruptions
    disrupted_regions: set[str] = {
        str(d.get("affected_region") or "").strip().lower()
        for d in active_disruptions
        if d.get("affected_region")
    }

    options: list[CarrierOption] = []

    for carrier in all_carriers:
        if not carrier.get("active", True):
            continue

        # Skip current carrier
        if str(carrier.get("id") or "") == current_carrier_id:
            continue

        reliability = float(carrier.get("reliability_score") or 0.7)
        cost_index = float(carrier.get("cost_index") or 1.0)
        coverage: list[str] = [
            str(r).strip().lower()
            for r in (carrier.get("coverage_regions") or [])
        ]

        # Check if this carrier's coverage regions overlap with active disruption regions
        in_disruption_zone = bool(
            disrupted_regions & set(coverage)
        )
        if in_disruption_zone:
            continue  # skip carriers also in disruption zone

        # Score: reliability / cost_index  (higher reliability + lower cost = better)
        score = reliability / max(0.01, cost_index)

        # Coverage check against destination
        covers = _covers_destination(coverage, destination)
        if not covers:
            # Still include but penalise score
            score *= 0.6

        carrier_id = str(carrier["id"])
        name = str(carrier.get("name") or "")
        code = str(carrier.get("code") or "")

        region_note = (
            f"covers {destination} region"
            if covers
            else f"limited coverage for {destination}"
        )
        reason = (
            f"Carrier {name} — reliability {reliability:.2f}, "
            f"cost index {cost_index:.2f} "
            f"({'%.0f' % ((1 - cost_index) * 100)}% "
            f"{'below' if cost_index < 1 else 'above'} baseline), "
            f"{region_note}."
        )

        options.append(
            CarrierOption(
                carrier_id=carrier_id,
                carrier_name=name,
                carrier_code=code,
                score=round(score, 4),
                reliability_score=round(reliability, 4),
                cost_index=round(cost_index, 4),
                covers_region=covers,
                reason=reason,
            )
        )

    options.sort(key=lambda o: -o.score)
    return options[:top_n]


def _covers_destination(coverage_regions: list[str], destination: str) -> bool:
    """Check if any coverage region is a substring of or matches destination."""
    dest_lower = destination.lower()
    for region in coverage_regions:
        r = region.lower()
        if r and (r in dest_lower or dest_lower.startswith(r[:4])):
            return True
    return False
