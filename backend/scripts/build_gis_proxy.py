"""Build a documented susceptibility proxy from real GIS rasters.

DEM is required. Land-cover and soil rasters are optional, but rows are marked
INCOMPLETE when an optional layer is absent. This is a derived proxy, not an
official GSI/ISRO susceptibility product.
"""

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.transform import rowcol


def sample(raster: rasterio.DatasetReader, longitude: float, latitude: float) -> float | None:
    try:
        row, col = rowcol(raster.transform, longitude, latitude)
        if row < 0 or col < 0 or row >= raster.height or col >= raster.width:
            return None
        value = raster.read(1, window=Window(col, row, 1, 1))[0, 0]
        if raster.nodata is not None and value == raster.nodata:
            return None
        if not np.isfinite(value):
            return None
        return float(value)
    except (IndexError, ValueError):
        return None


def slope_degrees(raster: rasterio.DatasetReader, longitude: float, latitude: float) -> float | None:
    value = sample(raster, longitude, latitude)
    if value is None:
        return None
    row, col = rowcol(raster.transform, longitude, latitude)
    window = raster.read(1, window=Window(max(0, col - 1), max(0, row - 1), 3, 3))
    valid = window[np.isfinite(window)]
    if len(valid) < 3:
        return None
    # A 3x3 elevation window is used only for a local proxy. Geographic
    # pixel-size conversion keeps the result in degrees rather than pixels.
    pixel_x = abs(raster.transform.a)
    pixel_y = abs(raster.transform.e)
    if raster.crs and raster.crs.is_geographic:
        meters_per_degree = 111_320
        pixel_x *= meters_per_degree * max(math.cos(math.radians(latitude)), 0.1)
        pixel_y *= meters_per_degree
    if pixel_x <= 0 or pixel_y <= 0:
        return None
    gy, gx = np.gradient(window.astype(float), pixel_y, pixel_x)
    center = (window.shape[0] // 2, window.shape[1] // 2)
    return float(np.degrees(np.arctan(np.hypot(gx[center], gy[center]))))


def normalize(value: float | None, low: float, high: float) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, (value - low) / (high - low)))


def build(events: Path, dem: Path, output: Path, landcover: Path | None, soil: Path | None) -> dict:
    missing = [str(path) for path in (dem, landcover, soil) if path is not None and not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing GIS raster file(s):\n- "
            + "\n- ".join(missing)
            + "\nDownload the rasters and place them at these paths before running the proxy builder."
        )
    with events.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    dem_raster = rasterio.open(dem)
    landcover_raster = rasterio.open(landcover) if landcover else None
    soil_raster = rasterio.open(soil) if soil else None
    rows = []
    for source in source_rows:
        latitude = float(source["latitude"])
        longitude = float(source["longitude"])
        slope = slope_degrees(dem_raster, longitude, latitude)
        landcover_value = sample(landcover_raster, longitude, latitude) if landcover_raster else None
        soil_value = sample(soil_raster, longitude, latitude) if soil_raster else None
        components = [item for item in (
            normalize(slope, 0, 45),
            landcover_value if landcover_raster else None,
            soil_value if soil_raster else None,
        ) if item is not None]
        proxy = round(float(np.mean(components)), 4) if components else None
        coverage = "COMPLETE" if slope is not None and landcover_value is not None and soil_value is not None else "INCOMPLETE"
        rows.append({
            "location_id": source.get("slide_id") or source.get("serial_number"),
            "observed_at": source.get("event_date") or "",
            "latitude": latitude,
            "longitude": longitude,
            "slope_degrees": round(slope, 4) if slope is not None else "",
            "landcover_value": landcover_value if landcover_value is not None else "",
            "soil_value": soil_value if soil_value is not None else "",
            "susceptibility_index": proxy if proxy is not None else "",
            "susceptibility_index_source": "DERIVED_GIS_PROXY",
            "proxy_components": "slope,landcover,soil",
            "label_coverage": coverage,
            "is_demo": "false",
        })
    dem_raster.close()
    if landcover_raster:
        landcover_raster.close()
    if soil_raster:
        soil_raster.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return {
        "input_rows": len(source_rows),
        "output_rows": len(rows),
        "complete_rows": sum(row["label_coverage"] == "COMPLETE" for row in rows),
        "output": str(output),
        "source": "DERIVED_GIS_PROXY",
        "weights": "equal mean of normalized slope, pre-scored land-cover, and pre-scored soil components",
        "dem": str(dem),
        "landcover": str(landcover) if landcover else None,
        "soil": str(soil) if soil else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a derived GIS susceptibility proxy.")
    parser.add_argument("--events", type=Path, default=Path("data/interim/field_validated_inventory.csv"))
    parser.add_argument("--dem", type=Path, required=True)
    parser.add_argument("--landcover", type=Path, help="Raster whose cells are already scored from 0 to 1.")
    parser.add_argument("--soil", type=Path, help="Raster whose cells are already scored from 0 to 1.")
    parser.add_argument("--output", type=Path, default=Path("data/interim/gis_susceptibility_proxy.csv"))
    args = parser.parse_args()
    try:
        result = build(args.events, args.dem, args.output, args.landcover, args.soil)
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
