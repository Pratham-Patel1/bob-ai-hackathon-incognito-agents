"""
PredictiveRiskEngine — Phase 2B

Loads the pre-trained Random Forest artifact (risk_model.joblib) and
returns delay probability and predicted delay hours for a shipment.

Contract
--------
- The model is loaded ONCE at module import time (lazy singleton).
- If the artifact is absent, the engine degrades gracefully and returns None.
- No DB access occurs inside this file.
- The caller (router / service) passes a plain dict of features.

Input feature dict keys (all numeric / float):
    disruption_severity_score   0–4  (0=none, 1=low, 2=med, 3=high, 4=critical)
    cargo_value_usd             raw dollar amount (engine converts to log10)
    priority_encoded            0=low, 1=medium, 2=high, 3=critical
    distance_km                 route distance in km
    carrier_reliability         historical on-time rate 0.0–1.0
    temperature_required        0 or 1
    is_hazmat                   0 or 1
    weather_severity            0–4
    route_risk_index            0.0–1.0
    hours_until_deadline        hours remaining
    shipment_age_hours          hours since scheduled departure

Output
------
PredictiveRiskResult dataclass:
    delay_probability      float  0.0–1.0
    delay_risk_score       float  0–100  (probability × 100)
    predicted_delay_hours  float  estimated hours of delay
    model_version          str
    available              bool   False if artifact missing
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Artifact path
# ---------------------------------------------------------------------------

_ARTIFACT_PATH = Path(__file__).parent.parent / "ml" / "risk_model.joblib"

# ---------------------------------------------------------------------------
# Lazy model loader
# ---------------------------------------------------------------------------

_MODEL_CACHE: Optional[Dict[str, Any]] = None
_LOAD_ATTEMPTED = False


def _load_model() -> Optional[Dict[str, Any]]:
    global _MODEL_CACHE, _LOAD_ATTEMPTED
    if _LOAD_ATTEMPTED:
        return _MODEL_CACHE
    _LOAD_ATTEMPTED = True
    if not _ARTIFACT_PATH.exists():
        return None
    try:
        import joblib
        _MODEL_CACHE = joblib.load(_ARTIFACT_PATH)
    except Exception:
        _MODEL_CACHE = None
    return _MODEL_CACHE


# ---------------------------------------------------------------------------
# Delay hour estimation table
# (mapped from delay probability buckets)
# ---------------------------------------------------------------------------

def _estimate_delay_hours(delay_probability: float, disruption_severity_score: float) -> float:
    """
    Estimate delay hours from probability and disruption severity.
    Uses a simple lookup + severity multiplier — no ML regression needed for MVP.
    """
    base_hours_map = [
        (0.85, 36.0),
        (0.70, 24.0),
        (0.55, 16.0),
        (0.40, 10.0),
        (0.25, 6.0),
        (0.10, 3.0),
        (0.00, 0.0),
    ]
    base = 0.0
    for threshold, hours in base_hours_map:
        if delay_probability >= threshold:
            base = hours
            break

    # Severity multiplier: score 0..4 → factor 1.0..1.75
    severity_multiplier = 1.0 + (disruption_severity_score / 4.0) * 0.75
    return round(base * severity_multiplier, 1)


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class PredictiveRiskResult:
    delay_probability: float
    delay_risk_score: float
    predicted_delay_hours: float
    model_version: str
    available: bool


# ---------------------------------------------------------------------------
# Engine function
# ---------------------------------------------------------------------------

def predict_shipment_risk(features: Dict[str, Any]) -> PredictiveRiskResult:
    """
    Run ML inference and return delay probability for a shipment.

    Parameters
    ----------
    features : dict
        Must contain the keys listed in the module docstring.
        Missing numeric values default to 0.

    Returns
    -------
    PredictiveRiskResult
        If model artifact is unavailable, returns a result with
        available=False and delay_probability=0.0.
    """
    artifact = _load_model()

    if artifact is None:
        return PredictiveRiskResult(
            delay_probability=0.0,
            delay_risk_score=0.0,
            predicted_delay_hours=0.0,
            model_version="unavailable",
            available=False,
        )

    pipeline = artifact["pipeline"]
    feature_columns = artifact["feature_columns"]
    model_version = artifact.get("model_version", "unknown")

    # Build feature vector in the exact order the model expects
    import numpy as np

    cargo_value_raw = float(features.get("cargo_value_usd") or 1)
    cargo_value_log = math.log10(max(cargo_value_raw, 1))

    row = {
        "disruption_severity_score": float(features.get("disruption_severity_score") or 0),
        "cargo_value_usd_log": cargo_value_log,
        "priority_encoded": float(features.get("priority_encoded") or 0),
        "distance_km": float(features.get("distance_km") or 0),
        "carrier_reliability": float(features.get("carrier_reliability") or 0.8),
        "temperature_required": float(features.get("temperature_required") or 0),
        "is_hazmat": float(features.get("is_hazmat") or 0),
        "weather_severity": float(features.get("weather_severity") or 0),
        "route_risk_index": float(features.get("route_risk_index") or 0),
        "hours_until_deadline": float(features.get("hours_until_deadline") or 48),
        "shipment_age_hours": float(features.get("shipment_age_hours") or 0),
    }

    X = np.array([[row[col] for col in feature_columns]])
    prob = float(pipeline.predict_proba(X)[0][1])
    delay_risk_score = round(prob * 100, 2)

    disruption_sev = float(features.get("disruption_severity_score") or 0)
    predicted_hours = _estimate_delay_hours(prob, disruption_sev)

    return PredictiveRiskResult(
        delay_probability=round(prob, 4),
        delay_risk_score=delay_risk_score,
        predicted_delay_hours=predicted_hours,
        model_version=model_version,
        available=True,
    )


def reload_model() -> None:
    """Force reload the model artifact from disk. Useful after retraining."""
    global _MODEL_CACHE, _LOAD_ATTEMPTED
    _MODEL_CACHE = None
    _LOAD_ATTEMPTED = False
    _load_model()
