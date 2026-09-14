"""Collect public historical rainfall and wetness predictors.

Open-Meteo's archive endpoint provides ERA5-Land reanalysis values without an
account. These are useful as a transparent fallback when direct IMERG/SMAP
downloads are unavailable. They are not satellite observations and are kept
explicitly labeled as reanalysis in the output and manifest.
"""

import argparse
import csv
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://archive-api.open-meteo.com/v1/archive"
NORTHEAST_BBOX = (88.0, 21.5, 97.5, 29.8)


def fetch(events: list[dict], start: date, end: date) -> list[dict]:
    params = urlencode({
        "latitude": ",".join(str(event["latitude"]) for event in events),
        "longitude": ",".join(str(event["longitude"]) for event in events),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "precipitation_sum,soil_moisture_0_to_7cm_mean",
        "timezone": "UTC",
    })
    request = Request(
        f"{API_URL}?{params}",
        headers={"User-Agent": "LandslideGuard-NER/1.0 predictor-collector"},
    )
    for attempt in range(4):
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.load(response)
                return payload if isinstance(payload, list) else [payload]
        except (HTTPError, URLError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Weather request failed after retries.")


def read_events(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    events = []
    for row in rows:
        if not row.get("event_date") or not row.get("latitude") or not row.get("longitude"):
            continue
        events.append({
            "event_id": row.get("slide_id") or row.get("serial_number") or row.get("event_id") or "event",
            "event_date": date.fromisoformat(row["event_date"]).isoformat(),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
        })
    west, south, east, north = NORTHEAST_BBOX
    return [
        event for event in events
        if west <= event["longitude"] <= east and south <= event["latitude"] <= north
    ]


def collect(events_path: Path, output: Path, manifest: Path, lookback_days: int, limit: int | None) -> dict:
    events = read_events(events_path)
    if limit is not None:
        events = events[:limit]
    rows = []
    failures = []
    groups: dict[tuple[date, date], list[dict]] = {}
    for event in events:
        event_day = date.fromisoformat(event["event_date"])
        start = event_day - timedelta(days=lookback_days)
        groups.setdefault((start, event_day - timedelta(days=1)), []).append(event)

    processed = 0
    for (start, end), grouped_events in groups.items():
        for offset in range(0, len(grouped_events), 100):
            batch = grouped_events[offset:offset + 100]
            try:
                payloads = fetch(batch, start, end)
                if len(payloads) != len(batch):
                    raise ValueError("Weather API returned an unexpected number of locations.")
                for event, payload in zip(batch, payloads):
                    daily = payload.get("daily") or {}
                    times = daily.get("time") or []
                    rain = daily.get("precipitation_sum") or []
                    moisture = daily.get("soil_moisture_0_to_7cm_mean") or []
                    for position, (observed_at, rainfall) in enumerate(zip(times, rain)):
                        soil_moisture = moisture[position] if position < len(moisture) else None
                        rainfall_window = [
                            value for value in rain[max(0, position - 29):position + 1]
                            if value is not None
                        ]
                        rain_3d = rain[max(0, position - 2):position + 1]
                        rain_7d = rain[max(0, position - 6):position + 1]
                        rows.append({
                            "location_id": f"{event['event_id']}:{observed_at}",
                            "observed_at": observed_at,
                            "latitude": event["latitude"],
                            "longitude": event["longitude"],
                            "rainfall_mm": rainfall if rainfall is not None else "",
                            "rainfall_3d_mm": round(sum(value for value in rain_3d if value is not None), 3),
                            "rainfall_7d_mm": round(sum(value for value in rain_7d if value is not None), 3),
                            "rainfall_30d_mm": round(sum(rainfall_window), 3),
                            "soil_moisture_ratio": soil_moisture if soil_moisture is not None else "",
                            "slope_degrees": "",
                            "susceptibility_index": "",
                            "is_demo": "false",
                            "label_coverage": "INCOMPLETE",
                            "rainfall_source": "ERA5_LAND_REANALYSIS_VIA_OPEN_METEO",
                            "soil_moisture_source": "ERA5_LAND_REANALYSIS_VIA_OPEN_METEO",
                            "source_event_id": event["event_id"],
                        })
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
                failures.extend({"event_id": event["event_id"], "error": str(error)} for event in batch)
            processed += len(batch)
            if processed % 100 == 0 or processed == len(events):
                print(f"Processed {processed}/{len(events)} event locations", flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else [
        "location_id", "observed_at", "latitude", "longitude", "rainfall_mm",
        "rainfall_3d_mm", "rainfall_7d_mm", "rainfall_30d_mm",
        "soil_moisture_ratio", "slope_degrees", "susceptibility_index",
        "is_demo", "label_coverage", "rainfall_source",
        "soil_moisture_source", "source_event_id",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        "source": "Open-Meteo archive / ERA5-Land",
        "api_url": API_URL,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "input_events": len(events),
        "output_rows": len(rows),
        "failed_events": failures,
        "lookback_days": lookback_days,
        "variables": {
            "rainfall_mm": "daily precipitation sum in millimetres",
            "soil_moisture_ratio": "0-7 cm volumetric soil water fraction",
        },
        "limitations": [
            "ERA5-Land is reanalysis, not direct satellite measurement.",
            "The output is incomplete until slope and susceptibility are joined.",
            "Event-day and future values are excluded to reduce label leakage.",
        ],
    }, indent=2), encoding="utf-8")
    return {"events_processed": len(events), "rows_written": len(rows), "failed_events": len(failures), "output": str(output)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public rainfall and wetness predictors.")
    parser.add_argument("--events", type=Path, default=Path("data/interim/field_validated_dated_events.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/weather_predictors.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/weather_predictors.json"))
    parser.add_argument("--lookback-days", type=int, default=30)
    parser.add_argument("--limit", type=int, help="Process only the first N events for a trial run.")
    args = parser.parse_args()
    print(json.dumps(collect(args.events, args.output, args.manifest, args.lookback_days, args.limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
