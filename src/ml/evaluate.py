"""
Evaluation report for the SupplyChainOS risk model artifact.

Loads the committed artifact and prints detailed metrics on a fresh
synthetic test set (so it works without requiring training_data.csv).

Usage:
    python src/ml/evaluate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import joblib
import numpy as np
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)

from generate_training_data import generate_record
import random

ARTIFACT_PATH = Path(__file__).parent / "artifacts" / "risk_model.joblib"
EVAL_SEED = 999
N_EVAL = 1000


def main() -> None:
    if not ARTIFACT_PATH.exists():
        print(f"ERROR: Artifact not found at {ARTIFACT_PATH}")
        print("Run: python src/ml/train.py")
        sys.exit(1)

    model = joblib.load(ARTIFACT_PATH)
    meta = getattr(model, "metadata", {})

    print("── Artifact Metadata ────────────────────────────────────────────")
    for k, v in meta.items():
        print(f"  {k}: {v}")

    # Generate fresh evaluation set
    rng = random.Random(EVAL_SEED)
    numpy_rng = np.random.default_rng(EVAL_SEED)

    from features import FEATURE_NAMES
    records = [generate_record(rng, numpy_rng) for _ in range(N_EVAL)]
    X_eval = np.array(
        [[r[f] for f in FEATURE_NAMES] for r in records], dtype=np.float32
    )
    y_eval = np.array([r["was_delayed"] for r in records], dtype=np.int32)

    y_pred = model.predict(X_eval)
    y_proba = model.predict_proba(X_eval)[:, 1]

    f1 = f1_score(y_eval, y_pred, average="binary")
    roc_auc = roc_auc_score(y_eval, y_proba)

    print(f"\n── Evaluation on {N_EVAL} fresh synthetic records ───────────────")
    print(classification_report(y_eval, y_pred, target_names=["on_time", "delayed"]))
    print(f"F1 (binary): {f1:.4f}")
    print(f"ROC-AUC:     {roc_auc:.4f}")

    print("\n── Confusion Matrix ─────────────────────────────────────────────")
    cm = confusion_matrix(y_eval, y_pred)
    print(f"  TN={cm[0,0]}  FP={cm[0,1]}")
    print(f"  FN={cm[1,0]}  TP={cm[1,1]}")

    print("\n── Feature Importances ─────────────────────────────────────────")
    importances = model.feature_importances_
    for name, imp in sorted(
        zip(FEATURE_NAMES, importances), key=lambda x: -x[1]
    ):
        bar = "█" * int(imp * 40)
        print(f"  {name:<40} {imp:.4f} {bar}")


if __name__ == "__main__":
    main()
