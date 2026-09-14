# ML training gate

The current risk engine is a deterministic operational index. It must remain
the production fallback until a real labeled dataset passes
`python -m scripts.validate_training_data <file.csv>`.

The CSV must contain:

```text
location_id,observed_at,rainfall_mm,soil_moisture_ratio,slope_degrees,susceptibility_index,target_landslide,is_demo
```

Training is intentionally rejected when there are fewer than 50 rows, fewer
than three locations, fewer than ten positive landslide labels, missing feature
values, invalid labels/timestamps, or any demo rows. Evaluation must hold out
locations or time periods to prevent spatial and temporal leakage.

After the gate passes, install the backend requirements and run:

```powershell
cd backend
python -m scripts.train_model path\to\landslide_training.csv
```

The trainer uses a location-held-out split, so rows from a location never
appear in both training and evaluation. It writes an evaluation artifact to
`backend/artifacts/landslide-risk-model.joblib` and prints accuracy, F1,
ROC-AUC, average precision, and the held-out locations.

This artifact is not connected to the live API yet. Compare it with the
deterministic baseline and review the held-out locations before approving any
production integration. A model must not be described as predictive or
calibrated without that comparison and validation.
