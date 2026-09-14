"""Validate and normalize an official GSI/NGDR susceptibility export.

The NGDR portal requires an authenticated download. This script accepts the
GeoJSON export after download and preserves the original properties and
source metadata. It never treats an unverified file as official.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

NORTHEAST_BBOX = (88.0, 21.5, 97.5, 29.8)
EXPECTED_CLASSES = {
    "very low": 0.2,
    "low": 0.4,
    "moderate": 0.6,
    "high": 0.8,
    "very high": 1.0,
}


def in_bbox(coordinates: object) -> bool:
    if isinstance(coordinates, (list, tuple)):
        if len(coordinates) >= 2 and all(isinstance(value, (int, float)) for value in coordinates[:2]):
            lon, lat = coordinates[:2]
            return NORTHEAST_BBOX[0] <= lon <= NORTHEAST_BBOX[2] and NORTHEAST_BBOX[1] <= lat <= NORTHEAST_BBOX[3]
        return any(in_bbox(item) for item in coordinates)
    return False


def import_geojson(source: Path, output: Path, manifest: Path) -> dict:
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    if data.get("type") != "FeatureCollection":
        raise ValueError("GSI export must be a GeoJSON FeatureCollection.")
    features = data.get("features", [])
    if not features:
        raise ValueError("GSI export contains no features.")

    class_counts: dict[str, int] = {}
    northeast_features = 0
    missing_class = 0
    for feature in features:
        properties = feature.get("properties") or {}
        class_value = next(
            (str(properties[key]).strip() for key in properties if key.lower() in {
                "class", "susceptibility", "susceptibility_class", "hazard_class",
            } and properties[key] not in (None, "")),
            None,
        )
        if class_value is None:
            missing_class += 1
        else:
            normalized = class_value.casefold()
            class_counts[class_value] = class_counts.get(class_value, 0) + 1
            if normalized in EXPECTED_CLASSES:
                properties["susceptibility_index"] = EXPECTED_CLASSES[normalized]
        if in_bbox((feature.get("geometry") or {}).get("coordinates")):
            northeast_features += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data), encoding="utf-8")
    summary = {
        "source_file": str(source),
        "output_file": str(output),
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "features": len(features),
        "northeast_features": northeast_features,
        "class_counts": class_counts,
        "features_missing_class": missing_class,
        "source": "GSI_NGDR_OFFICIAL_EXPORT",
        "portal": "https://geodataindia.gov.in/guestuser",
        "download_requirement": "Authenticated NGDR registration/cart download",
        "limitations": [
            "Class field name is preserved from the export.",
            "Only recognized Very Low/Low/Moderate/High/Very High classes receive normalized values.",
            "The source export's CRS and methodology must be recorded from its metadata.",
            "Do not use this layer as both a predictor and target label.",
        ],
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Import an official GSI/NGDR susceptibility GeoJSON export.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/interim/gsi_ngdr_susceptibility.geojson"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/gsi_ngdr_susceptibility.json"))
    args = parser.parse_args()
    print(json.dumps(import_geojson(args.source, args.output, args.manifest), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
