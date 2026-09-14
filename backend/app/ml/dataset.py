import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REQUIRED_FEATURES = (
    "rainfall_mm",
    "soil_moisture_ratio",
    "slope_degrees",
    "susceptibility_index",
)
REQUIRED_COLUMNS = ("location_id", "observed_at", "target_landslide", "is_demo")


@dataclass(frozen=True)
class DatasetReport:
    rows: int
    locations: int
    positive_rows: int
    demo_rows: int
    missing_feature_rows: int
    invalid_rows: int
    ready_for_training: bool
    errors: tuple[str, ...]


def validate_training_csv(path: str | Path) -> DatasetReport:
    errors: list[str] = []
    rows = 0
    locations: set[str] = set()
    positive_rows = 0
    demo_rows = 0
    missing_feature_rows = 0
    invalid_rows = 0

    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing_columns = [
            column for column in (*REQUIRED_COLUMNS, *REQUIRED_FEATURES)
            if column not in columns
        ]
        if missing_columns:
            return DatasetReport(
                0, 0, 0, 0, 0, 0, False,
                (f"Missing required columns: {', '.join(missing_columns)}",),
            )

        for line_number, row in enumerate(reader, start=2):
            rows += 1
            location_id = (row.get("location_id") or "").strip()
            if location_id:
                locations.add(location_id)
            if location_id.upper().startswith("DEMO") or row.get("is_demo", "").lower() == "true":
                demo_rows += 1

            try:
                datetime.fromisoformat((row.get("observed_at") or "").replace("Z", "+00:00"))
                target = int(row["target_landslide"])
                if target not in (0, 1):
                    raise ValueError("target_landslide must be 0 or 1")
                if target == 1:
                    positive_rows += 1
                values = [float(row[name]) if row.get(name, "").strip() else None for name in REQUIRED_FEATURES]
                if any(value is None for value in values):
                    missing_feature_rows += 1
            except (TypeError, ValueError):
                invalid_rows += 1
                errors.append(f"Invalid row at CSV line {line_number}")

    if rows < 50:
        errors.append("At least 50 labeled rows are required before training.")
    if len(locations) < 3:
        errors.append("At least 3 distinct locations are required for location-held-out evaluation.")
    if positive_rows < 10:
        errors.append("At least 10 positive landslide rows are required.")
    if demo_rows:
        errors.append("Demo rows must be removed before model training.")
    if missing_feature_rows:
        errors.append("Training rows may not have missing feature values.")
    return DatasetReport(
        rows,
        len(locations),
        positive_rows,
        demo_rows,
        missing_feature_rows,
        invalid_rows,
        not errors,
        tuple(dict.fromkeys(errors)),
    )
