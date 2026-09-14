"""
ShipmentRiskEngine — Phase 2A-2

Computes a blended operational risk score for a shipment:
  Final Score = min(100, 0.60 × Deterministic + 0.40 × ML)

When no ML score is available (model not yet trained / N/A),
the deterministic score is used at full weight.

Input contract
--------------
The router/service layer fetches data from the database and passes
plain dictionaries to this engine.  No ORM sessions or DB access
happen inside this file.

shipment dict keys (matching Shipment model fields):
    id, tracking_number, status, cargo_type, cargo_value_usd,
    temperature_required, scheduled_arrival, estimated_arrival,
    disruption_impact_score (float | None)   <- from DisruptionImpactEngine result

Output
------
ShipmentRiskResult dataclass:
    risk_score          float   0–100
    risk_level          str     LOW | MEDIUM | HIGH | CRITICAL
    deterministic_score float
    ml_score            float | None
    factors             list[str]   human-readable explanations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class ShipmentRiskResult:
    risk_score: float
    risk_level: str
    deterministic_score: float
    ml_score: Optional[float]
    factors: List[str]


# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

# Cargo value thresholds (USD)
_CARGO_VALUE_HIGH = 100_000
_CARGO_VALUE_MED = 50_000

# Cargo value contributions
_CARGO_VALUE_HIGH_SCORE = 15
_CARGO_VALUE_MED_SCORE = 10
_CARGO_VALUE_LOW_SCORE = 5

# Priority contributions
_PRIORITY_SCORES: Dict[str, int] = {
    "critical": 20,
    "high": 15,
    "medium": 10,
    "low": 5,
}

# Deadline proximity thresholds (hours)
_DEADLINE_URGENT = 12
_DEADLINE_SOON = 24

# Deadline contributions
_DEADLINE_URGENT_SCORE = 20
_DEADLINE_SOON_SCORE = 10

# Cargo type bonuses
_TEMP_SENSITIVE_SCORE = 10
_HAZMAT_SCORE = 10

# Status bonus — already at risk / delayed
_AT_RISK_STATUS_SCORE = 10

# Blend weights
_DETERMINISTIC_WEIGHT = 0.60
_ML_WEIGHT = 0.40

# Risk level bands
_RISK_BANDS = [
    (75, "CRITICAL"),
    (50, "HIGH"),
    (25, "MEDIUM"),
    (0,  "LOW"),
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _risk_level_from_score(score: float) -> str:
    for threshold, level in _RISK_BANDS:
        if score >= threshold:
            return level
    return "LOW"


def _hours_until_deadline(scheduled_arrival: Any) -> Optional[float]:
    """Return hours until scheduled_arrival from now. Handles datetime and ISO strings."""
    if scheduled_arrival is None:
        return None
    if isinstance(scheduled_arrival, str):
        try:
            scheduled_arrival = datetime.fromisoformat(scheduled_arrival)
        except ValueError:
            return None
    # Make aware if naive
    if scheduled_arrival.tzinfo is None:
        scheduled_arrival = scheduled_arrival.replace(tzinfo=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    delta = scheduled_arrival - now
    return delta.total_seconds() / 3600


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def calculate_shipment_risk(
    shipment: Dict[str, Any],
    disruption_impact_score: Optional[float] = None,
    ml_risk_score: Optional[float] = None,
) -> ShipmentRiskResult:
    """
    Compute blended risk for a single shipment.

    Parameters
    ----------
    shipment : dict
        Flat dict matching Shipment model fields.
    disruption_impact_score : float | None
        Impact score (0–100) from DisruptionImpactEngine.
        Pass None if no active disruption affects this shipment.
    ml_risk_score : float | None
        Predicted probability (0–100) from PredictiveRiskEngine.
        Pass None until Phase 2B is complete; falls back to full
        deterministic weighting.

    Returns
    -------
    ShipmentRiskResult
    """
    raw_score = 0.0
    factors: List[str] = []

    # ------------------------------------------------------------------
    # 1. Disruption impact contribution (already 0–100 scale)
    # ------------------------------------------------------------------
    if disruption_impact_score is not None:
        # Normalise so it contributes proportionally (max 40 pts)
        contribution = round(disruption_impact_score * 0.40, 1)
        raw_score += contribution
        factors.append(f"Active disruption impact score {disruption_impact_score} (+{contribution})")

    # ------------------------------------------------------------------
    # 2. Cargo value
    # ------------------------------------------------------------------
    cargo_value = float(shipment.get("cargo_value_usd") or 0)
    if cargo_value >= _CARGO_VALUE_HIGH:
        raw_score += _CARGO_VALUE_HIGH_SCORE
        factors.append(f"High-value cargo ${cargo_value:,.0f} ≥ $100k (+{_CARGO_VALUE_HIGH_SCORE})")
    elif cargo_value >= _CARGO_VALUE_MED:
        raw_score += _CARGO_VALUE_MED_SCORE
        factors.append(f"Medium-value cargo ${cargo_value:,.0f} ≥ $50k (+{_CARGO_VALUE_MED_SCORE})")
    else:
        raw_score += _CARGO_VALUE_LOW_SCORE
        factors.append(f"Standard-value cargo ${cargo_value:,.0f} (+{_CARGO_VALUE_LOW_SCORE})")

    # ------------------------------------------------------------------
    # 3. Priority
    # ------------------------------------------------------------------
    priority = str(shipment.get("priority") or "low").lower()
    priority_score = _PRIORITY_SCORES.get(priority, _PRIORITY_SCORES["low"])
    raw_score += priority_score
    factors.append(f"{priority.capitalize()} priority shipment (+{priority_score})")

    # ------------------------------------------------------------------
    # 4. Deadline proximity
    # ------------------------------------------------------------------
    scheduled_arrival = shipment.get("scheduled_arrival") or shipment.get("estimated_arrival")
    hours_left = _hours_until_deadline(scheduled_arrival)
    if hours_left is not None:
        if hours_left <= _DEADLINE_URGENT:
            raw_score += _DEADLINE_URGENT_SCORE
            factors.append(
                f"Deadline critical — {hours_left:.1f}h remaining (≤ {_DEADLINE_URGENT}h) (+{_DEADLINE_URGENT_SCORE})"
            )
        elif hours_left <= _DEADLINE_SOON:
            raw_score += _DEADLINE_SOON_SCORE
            factors.append(
                f"Deadline approaching — {hours_left:.1f}h remaining (≤ {_DEADLINE_SOON}h) (+{_DEADLINE_SOON_SCORE})"
            )

    # ------------------------------------------------------------------
    # 5. Cargo type bonuses
    # ------------------------------------------------------------------
    cargo_type = str(shipment.get("cargo_type") or "").lower()
    temperature_required = bool(shipment.get("temperature_required") or False)

    if temperature_required or "temperature" in cargo_type:
        raw_score += _TEMP_SENSITIVE_SCORE
        factors.append(f"Temperature-sensitive cargo (+{_TEMP_SENSITIVE_SCORE})")

    if "hazmat" in cargo_type or "hazardous" in cargo_type:
        raw_score += _HAZMAT_SCORE
        factors.append(f"Hazardous material cargo (+{_HAZMAT_SCORE})")

    # ------------------------------------------------------------------
    # 6. Existing at-risk or delayed status
    # ------------------------------------------------------------------
    status = str(shipment.get("status") or "").lower()
    if status in ("at_risk", "delayed", "held"):
        raw_score += _AT_RISK_STATUS_SCORE
        factors.append(f"Shipment already '{status}' (+{_AT_RISK_STATUS_SCORE})")

    # ------------------------------------------------------------------
    # 7. Cap deterministic score at 100
    # ------------------------------------------------------------------
    deterministic_score = min(raw_score, 100.0)

    # ------------------------------------------------------------------
    # 8. Blend with ML score if available
    # ------------------------------------------------------------------
    if ml_risk_score is not None:
        ml_clamped = min(max(float(ml_risk_score), 0.0), 100.0)
        blended = _DETERMINISTIC_WEIGHT * deterministic_score + _ML_WEIGHT * ml_clamped
        final_score = round(min(blended, 100.0), 2)
        factors.append(
            f"ML predictive risk score {ml_clamped:.1f} blended at {int(_ML_WEIGHT*100)}% weight"
        )
    else:
        # No ML model yet — use deterministic at full weight
        final_score = round(deterministic_score, 2)

    risk_level = _risk_level_from_score(final_score)

    return ShipmentRiskResult(
        risk_score=final_score,
        risk_level=risk_level,
        deterministic_score=round(deterministic_score, 2),
        ml_score=round(ml_risk_score, 2) if ml_risk_score is not None else None,
        factors=factors,
    )
