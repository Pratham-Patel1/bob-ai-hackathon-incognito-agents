# ML Training Pipeline — SupplyChainOS Risk Model

## Overview

This directory contains the **offline training pipeline** for the shipment delay risk prediction model.

- The trained artifact (`artifacts/risk_model.joblib`) is committed to the repository.
- The application **loads** the artifact at startup — it never trains at runtime.
- Re-run this pipeline when you want to retrain with new data or updated features.

---

## Prerequisites

```bash
pip install -r requirements.txt
```

Python 3.11 is required. On Python 3.14 (no scikit-learn wheels), run inside Docker:

```bash
docker compose run --rm backend python ml/generate_training_data.py
docker compose run --rm backend python ml/train.py
```

---

## Retraining Steps

### 1. Generate training data

```bash
python src/ml/generate_training_data.py
```

Outputs: `src/ml/training_data.csv` (~5,000 rows, gitignored)

### 2. Train and save artifact

```bash
python src/ml/train.py
```

- Trains `RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)`
- Validates F1 ≥ 0.70 on the held-out test set
- Saves artifact to `src/ml/artifacts/risk_model.joblib`
- Aborts (without saving) if F1 is below threshold

### 3. Evaluate (optional)

```bash
python src/ml/evaluate.py
```

Prints full classification report + confusion matrix + feature importances.

### 4. Commit updated artifact

```bash
git add src/ml/artifacts/risk_model.joblib
git commit -m "chore: retrain risk model vX"
```

---

## Feature Engineering

Feature extraction is in `features.py` — used by **both** the training pipeline and the inference engine (`src/backend/engines/predictive_risk.py`).

**If you change `features.py`, you must retrain the model.** The two must stay in sync.

| Feature | Description |
|---|---|
| `days_to_scheduled_arrival` | Days remaining until scheduled delivery |
| `historical_route_delay_rate` | 1 - route.reliability_score |
| `carrier_reliability_score` | Carrier historical on-time % |
| `cargo_sensitivity_score` | temp_sensitive=1.0, hazmat=0.8, fragile=0.6, general=0.3 |
| `simultaneous_disruption_count` | Number of active disruptions for this shipment |
| `worst_disruption_severity_encoded` | low=1, medium=2, high=3, critical=4 (0 if none) |
| `hours_in_transit_pct` | How far through route (0.0–1.0) |
| `weight_kg_normalized` | weight_kg / 10000, clamped to [0, 1] |

---

## Files

| File | Purpose |
|---|---|
| `features.py` | Shared feature extraction (training + inference) |
| `generate_training_data.py` | Synthetic historical dataset generation |
| `train.py` | Training pipeline — saves artifact |
| `evaluate.py` | Evaluation report on fresh synthetic set |
| `artifacts/risk_model.joblib` | Committed pre-trained artifact |
| `training_data.csv` | Generated CSV (gitignored) |
