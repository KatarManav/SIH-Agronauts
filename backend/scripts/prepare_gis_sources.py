"""Prepare real GIS rasters for the Northeast India proxy workflow.

This command accepts downloaded source rasters and produces aligned local
rasters. It intentionally does not guess a susceptibility score from raw
categorical values; the mappings below are explicit and recorded in a
manifest for review.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject
from shapely.geometry import box, mapping

NORTHEAST_BBOX = (88.0, 21.5, 97.5, 29.8)
WORLDCOVER_RISK = {
    10: 0.25, 20: 0.35, 30: 0.45, 40: 0.55, 50: 0.75,
    60: 0.65, 70: 0.10, 80: 0.05, 90: 0.65, 95: 0.40, 100: 0.30,
}


def crop(source: Path, output: Path) -> None:
    with rasterio.open(source) as src:
        if src.crs is None:
            raise ValueError(f"{source} has no CRS.")
        geometry = [mapping(box(*NORTHEAST_BBOX))]
        data, transform = mask(src, geometry, crop=True, filled=True)
        profile = src.profile.copy()
        profile.update(height=data.shape[1], width=data.shape[2], transform=transform)
        output.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output, "w", **profile) as dst:
            dst.write(data)


def make_worldcover_score(source: Path, output: Path) -> None:
    with rasterio.open(source) as src:
        data = src.read(1)
        result = np.full(data.shape, np.nan, dtype="float32")
        for category, score in WORLDCOVER_RISK.items():
            result[data == category] = score
        profile = src.profile.copy()
        profile.update(dtype="float32", count=1, nodata=-9999)
        result[np.isnan(result)] = -9999
        output.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output, "w", **profile) as dst:
            dst.write(result, 1)


def make_soil_score(source: Path, output: Path, minimum: float, maximum: float) -> None:
    with rasterio.open(source) as src:
        data = src.read(1).astype("float32")
        valid = data != src.nodata if src.nodata is not None else np.isfinite(data)
        result = np.full(data.shape, -9999, dtype="float32")
        result[valid] = np.clip((data[valid] - minimum) / (maximum - minimum), 0, 1)
        profile = src.profile.copy()
        profile.update(dtype="float32", count=1, nodata=-9999)
        output.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output, "w", **profile) as dst:
            dst.write(result, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare downloaded GIS layers for Northeast India.")
    parser.add_argument("--dem", type=Path, required=True)
    parser.add_argument("--worldcover", type=Path, required=True)
    parser.add_argument("--soil", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/gis"))
    parser.add_argument("--soil-min", type=float, required=True, help="Lower bound for the chosen soil property.")
    parser.add_argument("--soil-max", type=float, required=True, help="Upper bound for the chosen soil property.")
    args = parser.parse_args()
    if not args.dem.exists() or not args.worldcover.exists() or not args.soil.exists():
        missing = [str(p) for p in (args.dem, args.worldcover, args.soil) if not p.exists()]
        parser.error("Missing downloaded source file(s): " + ", ".join(missing))
    out = args.output_dir
    crop(args.dem, out / "dem.tif")
    crop(args.worldcover, out / "worldcover.tif")
    crop(args.soil, out / "soil_property.tif")
    make_worldcover_score(out / "worldcover.tif", out / "landcover_risk_score.tif")
    make_soil_score(out / "soil_property.tif", out / "soil_risk_score.tif", args.soil_min, args.soil_max)
    (out / "gis_proxy_manifest.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bbox": NORTHEAST_BBOX,
        "sources": {"dem": str(args.dem), "worldcover": str(args.worldcover), "soil": str(args.soil)},
        "worldcover_risk_mapping": WORLDCOVER_RISK,
        "soil_normalization": {"minimum": args.soil_min, "maximum": args.soil_max},
        "warning": "Derived GIS proxy only; not an official GSI susceptibility map.",
    }, indent=2), encoding="utf-8")
    print(f"Prepared GIS rasters under {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
