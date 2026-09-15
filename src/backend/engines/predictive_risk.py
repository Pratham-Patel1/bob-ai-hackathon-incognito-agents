"""
PredictiveRiskEngine — ML-based delay probability inference.

Pure Python — no FastAPI or SQLAlchemy imports.
Loads pre-trained RandomForest artifact at module init (once per process).
Falls back gracefully if artifact is missing.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# ── Artifact loading (once at module import) ──────────────────────────────────
# Path: from the engine file → ../../ml/artifacts/risk_model.joblib
# Inside Docker: /app/ml/artifacts/risk_model.joblib  (PYTHONPATH=/app)
_ARTIFACT_PATH = Path(__file__).parent.parent.parent / "ml" / "artifacts" / "risk_model.joblib"

_model = None
_model_version = "unknown"
_feature_importances: list[float] = []

try:
    _model = joblib.load(_ARTIFACT_PATH)
    _model_version = getattr(_model, "metadata", {}).get("version", "unknown")
    _feature_importances = list(_model.feature_importances_)
    logger.info(
        "PredictiveRiskEngine: loaded artifact version=%s from %s",
        _model_version,
        _ARTIFACT_PATH,
    )
except FileNotFoundError:
    logger.warning(
        "PredictiveRiskEngine: artifact not found at %s — ML scores will be None",
        _ARTIFACT_PATH,
    )
except Exception as exc:
    logger.warning(
        "PredictiveRiskEngine: failed to load artifact: %s — ML scores will be None",
        exc,
    )

# Import feature extraction — sys.path must include the ml/ directory
# We add it here to support both Docker (/app) and local test execution.
_ml_path = Path(__file__).parent.parent.parent / "ml"
if str(_ml_path) not in sys.path:
    sys.path.insert(0, str(_ml_path))

try:
    from features import FEATURE_NAMES, extract_features as _extract_features
    _features_available = True
except ImportError:
    logger.warning("PredictiveRiskEngine: cannot import features.py — ML scores will be None")
    _features_available = False


@dataclass
class FeatureContribution:
    feature_name: str
    value: float
    importance: float


@dataclass
class MLRiskResult:
    ml_score: float | None          # None if model unavailable
    top_features: list[FeatureContribution] = field(default_factory=list)
    model_version: str = "unknown"


def run(
    shipment: dict[str, Any],
    active_disruptions: list[dict[str, Any]],
    carrier: dict[str, Any],
) -> MLRiskResult:
    """
    Predict delay probability for a shipment.

    Args:
        shipment: dict with keys for feature extraction
        active_disruptions: list of disruption dicts (may be empty)
        carrier: dict with reliability_score

    Returns:
        MLRiskResult with ml_score in [0.0, 1.0] or None if model unavailable.
    """
    if _model is None or not _features_available:
        return MLRiskResult(ml_score=None, model_version=_model_version)

    try:
        features = _extract_features(shipment, active_disruptions, carrier)
        proba = _model.predict_proba(features.reshape(1, -1))[0]
        ml_score = float(proba[1])  # probability of class 1 = delayed

        # Top 3 feature contributions
        top_features = []
        if _feature_importances:
            pairs = sorted(
                zip(FEATURE_NAMES, features, _feature_importances),
                key=lambda x: -x[2],
            )[:3]
            for fname, fval, fimp in pairs:
                top_features.append(
                    FeatureContribution(
                        feature_name=fname,
                        value=round(float(fval), 4),
                        importance=round(float(fimp), 4),
                    )
                )

        return MLRiskResult(
            ml_score=round(ml_score, 4),
            top_features=top_features,
            model_version=_model_version,
        )

    except Exception as exc:
        logger.warning("PredictiveRiskEngine.run failed: %s", exc)
        return MLRiskResult(ml_score=None, model_version=_model_version)
