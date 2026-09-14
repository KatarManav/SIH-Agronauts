"""Train an XGBoost landslide classifier after the dataset safety gate passes.

This command creates an artifact for evaluation only. The live API continues to
use the deterministic risk engine until a model is explicitly approved.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBClassifier

from app.ml.dataset import REQUIRED_FEATURES, validate_training_csv


def train(csv_path: Path, artifact_path: Path, test_size: float, seed: int) -> dict:
    report = validate_training_csv(csv_path)
    if not report.ready_for_training:
        raise ValueError("Training data failed validation:\n- " + "\n- ".join(report.errors))

    frame = pd.read_csv(csv_path)
    features = frame.loc[:, REQUIRED_FEATURES]
    target = frame["target_landslide"].astype(int)
    groups = frame["location_id"]

    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_indexes, test_indexes = next(splitter.split(features, target, groups))
    x_train, x_test = features.iloc[train_indexes], features.iloc[test_indexes]
    y_train, y_test = target.iloc[train_indexes], target.iloc[test_indexes]

    if y_train.nunique() < 2 or y_test.nunique() < 2:
        raise ValueError(
            "Location-held-out split has only one target class in train or test. "
            "Collect more labeled locations and retry."
        )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=seed,
        n_jobs=1,
    )
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "f1": round(float(f1_score(y_test, predictions)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        "average_precision": round(float(average_precision_score(y_test, probabilities)), 4),
        "train_rows": len(train_indexes),
        "test_rows": len(test_indexes),
        "test_locations": sorted(groups.iloc[test_indexes].unique().tolist()),
    }

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "features": list(REQUIRED_FEATURES),
            "metrics": metrics,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "dataset": str(csv_path),
            "training_type": "LOCATION_HELD_OUT_EVALUATION",
        },
        artifact_path,
    )
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Train and evaluate the landslide risk model.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--artifact", type=Path, default=Path("artifacts/landslide-risk-model.joblib"))
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    metrics = train(args.csv_path, args.artifact, args.test_size, args.seed)
    print(json.dumps({"status": "trained", "artifact": str(args.artifact), "metrics": metrics}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
