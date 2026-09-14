"""Collect reported landslide events from NASA's Global Landslide Catalog.

This creates event labels only; it does not invent non-events or predictor
values. The resulting file must be reviewed and joined with time-matched
rainfall/terrain data before it is used for training.
"""

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SERVICE_URL = (
    "https://maps.nccs.nasa.gov/server/rest/services/"
    "global_landslide_catalog/glc_viewer_service/FeatureServer"
)
NORTHEAST_INDIA = (88.0, 21.5, 97.5, 29.8)
STATE_NAMES = {
    "arunachal pradesh",
    "assam",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "sikkim",
    "tripura",
}


def get_json(url: str, params: dict[str, str], attempts: int = 4) -> dict:
    request_url = f"{url}?{urlencode(params)}"
    for attempt in range(attempts):
        try:
            request = Request(
                request_url,
                headers={"User-Agent": "LandslideGuard-NER/1.0 data-collector"},
            )
            with urlopen(request, timeout=120) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise RuntimeError(
                    f"NASA GLC returned HTTP {error.code}. "
                    "The service may be unavailable; retry later or use an exported source file."
                ) from error
        except URLError as error:
            if attempt == attempts - 1:
                raise RuntimeError(
                    "NASA GLC could not be reached. Check the network or retry later."
                ) from error
        time.sleep(2 ** attempt)
    raise RuntimeError("NASA GLC request failed after retries.")


def pick(attributes: dict, *names: str):
    normalized = {key.lower(): value for key, value in attributes.items()}
    for name in names:
        value = normalized.get(name.lower())
        if value not in (None, ""):
            return value
    return None


def layers() -> list[dict]:
    metadata = get_json(SERVICE_URL, {"f": "json"})
    return metadata.get("layers", []) + metadata.get("tables", [])


def query_layer(layer_id: int) -> list[dict]:
    url = f"{SERVICE_URL}/{layer_id}/query"
    params = {
        "f": "json",
        "where": "1=1",
        "geometry": ",".join(str(value) for value in NORTHEAST_INDIA),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "resultRecordCount": "2000",
    }
    return get_json(url, params).get("features", [])


def collect(output: Path, manifest: Path) -> int:
    available_layers = layers()
    if not available_layers:
        raise RuntimeError("NASA GLC service returned no queryable layers.")

    features: list[dict] = []
    selected_layer = None
    for item in available_layers:
        try:
            candidate = query_layer(int(item["id"]))
        except (KeyError, ValueError, json.JSONDecodeError):
            continue
        if candidate:
            features = candidate
            selected_layer = item
            break

    if selected_layer is None:
        raise RuntimeError("NASA GLC returned no events in the Northeast India bounding box.")

    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for feature in features:
        attributes = feature.get("attributes") or {}
        geometry = feature.get("geometry") or {}
        latitude = geometry.get("y") or pick(attributes, "latitude", "lat")
        longitude = geometry.get("x") or pick(attributes, "longitude", "lon", "long")
        if latitude is None or longitude is None:
            continue
        region = str(pick(attributes, "country", "admin1", "state", "province") or "")
        if region and region.lower() not in STATE_NAMES and "india" not in region.lower():
            continue
        rows.append(
            {
                "event_id": str(pick(attributes, "event_id", "id", "objectid") or ""),
                "event_date": str(pick(attributes, "event_date", "event_date_time", "date") or ""),
                "latitude": latitude,
                "longitude": longitude,
                "country": pick(attributes, "country"),
                "region": region,
                "landslide_type": pick(attributes, "landslide_type", "type"),
                "source_url": pick(attributes, "source", "url", "link"),
                "label_source": "NASA_GLOBAL_LANDSLIDE_CATALOG",
                "is_demo": "false",
            }
        )

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [
            "event_id", "event_date", "latitude", "longitude", "country",
            "region", "landslide_type", "source_url", "label_source", "is_demo",
        ])
        writer.writeheader()
        writer.writerows(rows)

    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({
        "source": "NASA Global Landslide Catalog",
        "service_url": SERVICE_URL,
        "selected_layer": selected_layer,
        "bounding_box": NORTHEAST_INDIA,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "event_rows_written": len(rows),
        "limitations": [
            "Reported events are not an exhaustive inventory.",
            "The public export is current only through 2016-03-07.",
            "Rows are event labels only and require predictor joins.",
        ],
    }, indent=2), encoding="utf-8")
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect NASA GLC events for Northeast India.")
    parser.add_argument("--output", type=Path, default=Path("data/interim/nasa_glc_northeast_india.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/nasa_glc_northeast_india.json"))
    args = parser.parse_args()
    try:
        count = collect(args.output, args.manifest)
    except RuntimeError as error:
        parser.error(str(error))
    print(f"Wrote {count} verified-source event records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
