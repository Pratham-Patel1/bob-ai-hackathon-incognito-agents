"""
Offline training pipeline for the SupplyChainOS shipment delay risk model.

Steps:
  1. Load training_data.csv
  2. Build feature matrix X and labels y
  3. Stratified 80/20 train/test split
  4. Train RandomForestClassifier
  5. Evaluate: precision, recall, F1, ROC-AUC
  6. Validate F1 >= 0.70 (abort if below threshold)
  7. Attach .metadata dict to model object
  8. Save to src/ml/artifacts/risk_model.joblib

Usage:
    python src/ml/generate_training_data.py  # run first
    python src/ml/train.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root or from src/ml/
sys.path.insert(0, str(Path(__file__).parent))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from features import FEATURE_NAMES

TRAINING_DATA_PATH = Path(__file__).parent / "training_data.csv"
ARTIFACT_PATH = Path(__file__).parent / "artifacts" / "risk_model.joblib"
F1_THRESHOLD = 0.70
F1_AVERAGE = "weighted"   # weighted F1 is appropriate for imbalanced classes
RANDOM_STATE = 42


def train() -> None:
    # ── 1. Load data ────────────────────────────────────────────────────────
    if not TRAINING_DATA_PATH.exists():
        print(f"ERROR: {TRAINING_DATA_PATH} not found.")
        print("Run: python src/ml/generate_training_data.py")
        sys.exit(1)

    df = pd.read_csv(TRAINING_DATA_PATH)
    print(f"Loaded {len(df)} records from {TRAINING_DATA_PATH}")

    # ── 2. Feature matrix and labels ────────────────────────────────────────
    missing = [f for f in FEATURE_NAMES if f not in df.columns]
    if missing:
        print(f"ERROR: Missing columns in training data: {missing}")
        sys.exit(1)

    X = df[FEATURE_NAMES].values.astype(np.float32)
    y = df["was_delayed"].values.astype(np.int32)

    delayed_pct = y.mean() * 100
    print(f"Class distribution: delayed={delayed_pct:.1f}%, on_time={100 - delayed_pct:.1f}%")

    # ── 3. Stratified train/test split ──────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
    )
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")

    # ── 4. Train ─────────────────────────────────────────────────────────────
    print("Training RandomForestClassifier(n_estimators=200, max_depth=12)...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        class_weight="balanced",
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # ── 5. Evaluate ──────────────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    f1 = f1_score(y_test, y_pred, average=F1_AVERAGE)
    roc_auc = roc_auc_score(y_test, y_proba)

    print("\n-- Classification Report --")
    print(classification_report(y_test, y_pred, target_names=["on_time", "delayed"]))
    print(f"F1 ({F1_AVERAGE}): {f1:.4f}")
    print(f"ROC-AUC:     {roc_auc:.4f}")

    # Feature importances
    importances = model.feature_importances_
    print("\n-- Feature Importances --")
    for name, imp in sorted(
        zip(FEATURE_NAMES, importances), key=lambda x: -x[1]
    ):
        bar = "#" * int(imp * 40)
        print(f"  {name:<40} {imp:.4f} {bar}")

    # 6. Validate
    if f1 < F1_THRESHOLD:
        print(f"\nWARNING: F1={f1:.4f} is below threshold {F1_THRESHOLD}.")
        print("Artifact NOT saved. Review training data or model config.")
        sys.exit(1)

    print(f"\nOK: F1={f1:.4f} meets threshold {F1_THRESHOLD}")

    # 7. Attach metadata
    model.metadata = {
        "version": f"1.0.{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "test_f1": round(f1, 4),
        "f1_average": F1_AVERAGE,
        "test_roc_auc": round(roc_auc, 4),
        "feature_names": FEATURE_NAMES,
        "model_type": "RandomForestClassifier",
        "n_estimators": 200,
        "max_depth": 12,
        "f1_threshold": F1_THRESHOLD,
    }

    # 8. Save artifact
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACT_PATH)
    print(f"\nArtifact saved to: {ARTIFACT_PATH}")
    print(f"  Version: {model.metadata['version']}")
    print(f"  Size:    {ARTIFACT_PATH.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    train()
