"""
SupplyChainOS — ML Offline Training Script (Phase 2B)

Generates synthetic historical shipment records and trains a
Random Forest classifier to predict whether a shipment will be delayed.

The resulting model artifact is saved to:
    src/backend/ml/risk_model.joblib

IMPORTANT:
- This script is run ONCE offline, not on application startup.
- The application loads the pre-trained artifact via PredictiveRiskEngine.
- Re-run this script whenever the feature set or training logic changes.

Usage:
    python -m backend.ml.train
    OR
    python src/backend/ml/train.py
"""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Works whether run as module or script
_HERE = Path(__file__).parent
ARTIFACT_PATH = _HERE / "risk_model.joblib"
METADATA_PATH = _HERE / "model_metadata.json"

# ---------------------------------------------------------------------------
# Feature specification
# ---------------------------------------------------------------------------

FEATURE_COLUMNS = [
    "disruption_severity_score",   # 0–4 (none/low/medium/high/critical)
    "cargo_value_usd_log",         # log10(cargo_value_usd)
    "priority_encoded",            # 0=low 1=medium 2=high 3=critical
    "distance_km",                 # route distance
    "carrier_reliability",         # historical on-time rate 0.0–1.0
    "temperature_required",        # 0 or 1
    "is_hazmat",                   # 0 or 1
    "weather_severity",            # 0–4
    "route_risk_index",            # 0.0–1.0
    "hours_until_deadline",        # hours remaining until scheduled arrival
    "shipment_age_hours",          # how long shipment has been in transit
]

TARGET_COLUMN = "was_delayed"

MODEL_VERSION = "v1.0.0"

# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

SEED = 42
random.seed(SEED)
np.random.seed(SEED)


def _generate_synthetic_data(n_samples: int = 5000) -> pd.DataFrame:
    """
    Generate realistic synthetic historical shipment records.
    The delay label (was_delayed) is determined by a weighted combination
    of the risk features, ensuring the model learns meaningful patterns.
    """
    rng = np.random.default_rng(SEED)

    disruption_severity = rng.integers(0, 5, n_samples)           # 0=none..4=critical
    cargo_value_raw = rng.exponential(scale=40_000, size=n_samples).clip(1_000, 500_000)
    priority = rng.integers(0, 4, n_samples)                       # 0=low..3=critical
    distance_km = rng.uniform(50, 3_000, n_samples)
    carrier_reliability = rng.uniform(0.5, 1.0, n_samples)
    temperature_required = rng.integers(0, 2, n_samples)
    is_hazmat = rng.integers(0, 2, n_samples)
    weather_severity = rng.integers(0, 5, n_samples)
    route_risk_index = rng.uniform(0.0, 1.0, n_samples)
    hours_until_deadline = rng.uniform(1, 120, n_samples)
    shipment_age_hours = rng.uniform(0, 240, n_samples)

    # Engineered label: higher disruption, low carrier reliability,
    # bad weather, high route risk → more likely delayed
    delay_prob = (
        disruption_severity * 0.18
        + (1 - carrier_reliability) * 0.25
        + weather_severity * 0.12
        + route_risk_index * 0.15
        + (priority / 3.0) * 0.05
        + temperature_required * 0.05
        + is_hazmat * 0.05
        + (1 / (hours_until_deadline / 12 + 1)) * 0.10
        + rng.uniform(0, 0.1, n_samples)   # noise
    ).clip(0, 1)

    was_delayed = (rng.uniform(0, 1, n_samples) < delay_prob).astype(int)

    df = pd.DataFrame({
        "disruption_severity_score": disruption_severity.astype(float),
        "cargo_value_usd_log": np.log10(cargo_value_raw),
        "priority_encoded": priority.astype(float),
        "distance_km": distance_km,
        "carrier_reliability": carrier_reliability,
        "temperature_required": temperature_required.astype(float),
        "is_hazmat": is_hazmat.astype(float),
        "weather_severity": weather_severity.astype(float),
        "route_risk_index": route_risk_index,
        "hours_until_deadline": hours_until_deadline,
        "shipment_age_hours": shipment_age_hours,
        TARGET_COLUMN: was_delayed,
    })
    return df


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_and_save() -> None:
    print("=" * 60)
    print("SupplyChainOS — ML Training (Phase 2B)")
    print("=" * 60)

    print("\n[1/4] Generating synthetic historical data …")
    df = _generate_synthetic_data(n_samples=5000)
    print(f"      Rows: {len(df):,}  |  Delayed: {df[TARGET_COLUMN].sum():,} "
          f"({df[TARGET_COLUMN].mean():.1%})")

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    print("\n[2/4] Splitting train / test (80/20) …")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=SEED, stratify=y
    )

    print("\n[3/4] Training RandomForestClassifier …")
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=SEED,
            n_jobs=-1,
        )),
    ])
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)

    print("\n      Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["on_time", "delayed"]))
    print(f"      ROC-AUC: {auc:.4f}")

    print(f"\n[4/4] Saving artifact → {ARTIFACT_PATH}")
    artifact = {
        "pipeline": pipeline,
        "feature_columns": FEATURE_COLUMNS,
        "model_version": MODEL_VERSION,
        "train_samples": len(X_train),
        "roc_auc": round(auc, 4),
    }
    joblib.dump(artifact, ARTIFACT_PATH)
    print(f"      ✅  Saved  ({ARTIFACT_PATH.stat().st_size / 1024:.1f} KB)")
    print("\n[DONE] risk_model.joblib ready for PredictiveRiskEngine.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    train_and_save()
