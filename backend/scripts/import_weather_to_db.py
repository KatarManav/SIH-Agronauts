"""Import collected real weather observations and event locations into Supabase."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import EnvironmentalObservation, Location


def import_csv(path: Path) -> dict[str, int]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    events = {}
    for row in rows:
        event_id = row["source_event_id"]
        events.setdefault(event_id, row)

    observations_added = 0
    locations_added = 0
    with SessionLocal.begin() as db:
        for event_id, row in events.items():
            location_id = f"REAL-EVENT-{event_id}"[:64]
            location = db.get(Location, location_id)
            if location is None:
                location = Location(
                    id=location_id,
                    name=f"Reported landslide event {event_id}",
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                )
                db.add(location)
                locations_added += 1

        db.flush()
        existing = {
            (item.location_id, item.observed_at, item.source)
            for item in db.scalars(
                select(EnvironmentalObservation).where(
                    EnvironmentalObservation.source == "ERA5_LAND_REANALYSIS_VIA_OPEN_METEO"
                )
            ).all()
        }
        for row in rows:
            location_id = f"REAL-EVENT-{row['source_event_id']}"[:64]
            observed_at = datetime.fromisoformat(row["observed_at"])
            key = (location_id, observed_at, "ERA5_LAND_REANALYSIS_VIA_OPEN_METEO")
            if key in existing:
                continue
            values = {
                key: float(row[key])
                for key in (
                    "rainfall_mm",
                    "rainfall_3d_mm",
                    "rainfall_7d_mm",
                    "rainfall_30d_mm",
                    "soil_moisture_ratio",
                )
                if row.get(key, "") not in ("", None)
            }
            db.add(EnvironmentalObservation(
                location_id=location_id,
                source="ERA5_LAND_REANALYSIS_VIA_OPEN_METEO",
                data_class="WEATHER_REANALYSIS",
                observed_at=observed_at,
                values_json=json.dumps(values),
                is_demo=False,
            ))
            observations_added += 1
    return {
        "input_rows": len(rows),
        "locations_added": locations_added,
        "observations_added": observations_added,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import real weather observations into the API database.")
    parser.add_argument("--input", type=Path, default=Path("data/interim/weather_predictors.csv"))
    args = parser.parse_args()
    if not args.input.exists():
        parser.error(f"Input file does not exist: {args.input}")
    print(json.dumps(import_csv(args.input), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
