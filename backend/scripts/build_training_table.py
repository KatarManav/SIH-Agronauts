"""Join dated landslide events to real environmental observations.

The predictor file must be supplied by the user or an approved data adapter.
This script never invents rainfall, soil moisture, terrain values, or
non-event labels.
"""

import argparse
import csv
import math
from datetime import date, datetime, timedelta
from pathlib import Path

from app.ml.dataset import REQUIRED_FEATURES

PREDICTOR_COLUMNS = (
    "location_id",
    "observed_at",
    "latitude",
    "longitude",
    *REQUIRED_FEATURES,
    "is_demo",
    "label_coverage",
)


def parse_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def read_events(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    events = []
    for row in rows:
        if row.get("event_date") and row.get("latitude") and row.get("longitude"):
            events.append({
                "event_id": row.get("slide_id") or row.get("event_id"),
                "date": date.fromisoformat(row["event_date"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            })
    return events


def read_predictors(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in PREDICTOR_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Predictor file is missing columns: {', '.join(missing)}")
        return list(reader)


def build(events_path: Path, predictors_path: Path, output_path: Path, radius_km: float, window_days: int) -> dict:
    events = read_events(events_path)
    predictors = read_predictors(predictors_path)
    rows = []
    skipped = 0
    for sample in predictors:
        if sample.get("is_demo", "").strip().lower() == "true":
            skipped += 1
            continue
        if sample.get("label_coverage", "").strip().upper() != "COMPLETE":
            skipped += 1
            continue
        observed = parse_date(sample["observed_at"])
        lat, lon = float(sample["latitude"]), float(sample["longitude"])
        matching = [
            event for event in events
            if observed <= event["date"] <= observed + timedelta(days=window_days)
            and distance_km(lat, lon, event["latitude"], event["longitude"]) <= radius_km
        ]
        target = 1 if matching else 0
        rows.append({
            "location_id": sample["location_id"],
            "observed_at": sample["observed_at"],
            **{feature: sample[feature] for feature in REQUIRED_FEATURES},
            "target_landslide": target,
            "is_demo": "false",
            "label_source": "FIELD_VALIDATED_DATED_EVENTS",
            "matched_event_id": matching[0]["event_id"] if matching else "",
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "location_id", "observed_at", *REQUIRED_FEATURES, "target_landslide",
        "is_demo", "label_source", "matched_event_id",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return {
        "predictor_rows": len(predictors),
        "training_rows": len(rows),
        "skipped_rows": skipped,
        "positive_rows": sum(row["target_landslide"] == 1 for row in rows),
        "negative_rows": sum(row["target_landslide"] == 0 for row in rows),
        "radius_km": radius_km,
        "label_window_days": window_days,
        "output": str(output_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a labeled training table from real observations.")
    parser.add_argument("--events", type=Path, default=Path("data/interim/field_validated_dated_events.csv"))
    parser.add_argument("--predictors", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/processed/landslide_training.csv"))
    parser.add_argument("--radius-km", type=float, default=5.0)
    parser.add_argument("--window-days", type=int, default=3)
    args = parser.parse_args()
    import json
    print(json.dumps(build(args.events, args.predictors, args.output, args.radius_km, args.window_days), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
