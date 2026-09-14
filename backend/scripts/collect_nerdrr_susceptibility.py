"""Download and join the official NESAC/NERDRR susceptibility layer.

The service currently exposes the layer through WMS GeoJSON. This collector
keeps the original class/gridcode values and only normalizes gridcode 1..5 to
0.0..1.0 for later modeling. It does not claim coverage outside the supplied
bounding box.
"""

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LAYER = "lhz_shl_ixs_ajl_nh6"
SERVICE_URL = "https://geoserver.nesdr.gov.in/geoserver/NERDRR_NEW/wms"
DEFAULT_BBOX = (91.8461, 23.6892, 92.8975, 25.6028)


def fetch_geojson(bbox: tuple[float, float, float, float]) -> dict:
    params = {
        "service": "WMS",
        "version": "1.3.0",
        "request": "GetMap",
        "layers": LAYER,
        "styles": "",
        "crs": "CRS:84",
        "bbox": ",".join(str(value) for value in bbox),
        "width": "1000",
        "height": "1000",
        "format": "application/json;type=geojson",
    }
    request = Request(
        f"{SERVICE_URL}?{urlencode(params)}",
        headers={"User-Agent": "LandslideGuard-NER/1.0 data-collector"},
    )
    with urlopen(request, timeout=180) as response:
        return json.load(response)


def write_geojson(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def join_events(events_path: Path, geojson: dict, output: Path) -> int:
    # This deliberately writes susceptibility observations only. Slope,
    # rainfall, and soil moisture require separate real source layers.
    features = geojson.get("features", [])
    rows = []
    with events_path.open(encoding="utf-8-sig", newline="") as handle:
        for event in csv.DictReader(handle):
            lat = float(event["latitude"])
            lon = float(event["longitude"])
            matched = None
            for feature in features:
                geometry = feature.get("geometry") or {}
                if geometry.get("type") != "Polygon":
                    continue
                ring = geometry.get("coordinates", [[]])[0]
                if _point_in_polygon(lon, lat, ring):
                    matched = feature.get("properties") or {}
                    break
            if matched is None:
                continue
            gridcode = int(matched["gridcode"])
            rows.append({
                "location_id": event.get("slide_id") or event.get("serial_number"),
                "observed_at": event["event_date"],
                "latitude": lat,
                "longitude": lon,
                "susceptibility_index": round(gridcode / 5, 4),
                "susceptibility_class": matched.get("class"),
                "susceptibility_gridcode": gridcode,
                "susceptibility_source": "NESAC_NERDRR_LHZ_SHL_IXS_AJL_NH6",
                "is_demo": "false",
                "label_coverage": "INCOMPLETE",
            })
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else [
        "location_id", "observed_at", "latitude", "longitude",
        "susceptibility_index", "susceptibility_class",
        "susceptibility_gridcode", "susceptibility_source", "is_demo",
        "label_coverage",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _point_in_polygon(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    for index in range(len(ring)):
        x1, y1 = ring[index - 1]
        x2, y2 = ring[index]
        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / (y2 - y1) + x1
        )
        if intersects:
            inside = not inside
    return inside


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect NESAC/NERDRR susceptibility GeoJSON.")
    parser.add_argument("--events", type=Path, default=Path("data/interim/field_validated_dated_events.csv"))
    parser.add_argument("--geojson", type=Path, default=Path("data/raw/nerdrr_susceptibility.geojson"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/nerdrr_event_susceptibility.csv"))
    args = parser.parse_args()
    bbox = DEFAULT_BBOX
    data = fetch_geojson(bbox)
    write_geojson(args.geojson, data)
    matched = join_events(args.events, data, args.output)
    manifest = args.geojson.with_suffix(".manifest.json")
    manifest.write_text(json.dumps({
        "source": "NESAC/NERDRR",
        "layer": LAYER,
        "service_url": SERVICE_URL,
        "bbox": bbox,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "features": len(data.get("features", [])),
        "event_points_matched": matched,
        "class_mapping": {"1": "Very Low", "2": "Low", "3": "Moderate", "4": "High", "5": "Very High"},
        "coverage_note": "Shillong-Silchar-Aizawl corridor only; not all Northeast India.",
        "label_coverage_note": "Joined output is incomplete until rainfall, soil moisture, and slope are added.",
    }, indent=2), encoding="utf-8")
    print(json.dumps({"features": len(data.get("features", [])), "matched_events": matched}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
