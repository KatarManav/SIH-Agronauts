# Landslide training data plan

This directory is for downloaded and locally prepared datasets. Raw downloads
must not be committed. The current database seed is demo data and must never
be included in training.

## Recommended first dataset

Build a tabular early-warning dataset for Northeast India before attempting a
deep-learning image model:

1. **Labels:** verified landslide events from GSI/ISRO/NRSC or a clearly
   documented NASA COOLR/Global Landslide Catalog record.
2. **Rainfall:** IMD gridded rainfall where access is available; otherwise
   NASA GPM IMERG.
3. **Terrain:** SRTM/NASADEM or Copernicus DEM derivatives.
4. **Wetness:** SMAP soil moisture or ERA5-Land soil-water variables.
5. **Baseline:** NASA LHASA output for the same date and location, when
   available. This is a comparison feature, not the target label.

The first version should cover at least three districts or locations, several
monsoon seasons, and both event and non-event observations. A model trained
only on two pilot locations cannot be trusted.

## Required training table

The trainer currently accepts a CSV with these columns:

```text
location_id,observed_at,rainfall_mm,soil_moisture_ratio,slope_degrees,susceptibility_index,target_landslide,is_demo
```

Required rules:

- `target_landslide=1` only when a verified event occurred in the defined
  label window after `observed_at`.
- `target_landslide=0` only after checking that no event was recorded in the
  same label window; an unknown case must not be forced to zero.
- `location_id` must identify a spatial unit, not just a repeated generic
  name.
- `observed_at` must be the time at which predictor data was available.
- All predictor data must be from or before `observed_at`; future information
  causes leakage.
- `is_demo` must be `false` for every training row.
- Preserve source URLs, retrieval dates, spatial resolution, units, and
  license information in a separate manifest.

## Suggested directory layout

```text
data/
  raw/                 # original downloads; never commit
  interim/             # reprojections, clipped rasters, cleaned events
  processed/           # generated CSV used by the trainer
  manifests/           # source and transformation metadata
```

## Start collecting

From `backend/`, run the NASA event collector:

```powershell
python -m scripts.collect_glc
```

It writes the event inventory to `data/interim/` and records the query,
retrieval time, selected service layer, and limitations under
`data/manifests/`. The collector does not create negative labels or fill
rainfall/terrain values. Those steps require separate, time-aware joins.

## Parse the field-validated inventory

The field-validated `landslide_report.csv` is a quoted fixed-width export, not
a conventional comma-separated file. Parse it with:

```powershell
python -m scripts.parse_field_inventory
```

This creates:

- `data/interim/field_validated_inventory.csv` for spatial susceptibility work
- `data/interim/field_validated_dated_events.csv` for dated event joins
- `data/manifests/field_validated_inventory.json` for counts and limitations

Undated records are not treated as dated training labels.

## Join predictors to event labels

The dated event file is only a label source. To build the training table,
provide a real predictor observation CSV with:

```text
location_id,observed_at,latitude,longitude,rainfall_mm,soil_moisture_ratio,slope_degrees,susceptibility_index,is_demo,label_coverage
```

`label_coverage` must be `COMPLETE`; other values are skipped rather than
converted into negative labels. Then run:

```powershell
python -m scripts.build_training_table --predictors path\to\predictors.csv
```

The default label window is three days after each observation and the default
event matching radius is 5 km. Both are configurable. The output contains
positive matches, defensible covered non-event rows, and the matched event ID.
No feature values are imputed.

## Collect official susceptibility coverage

Download the NESAC/NERDRR susceptibility layer and join it to dated field
events:

```powershell
python -m scripts.collect_nerdrr_susceptibility
```

Outputs:

- `data/raw/nerdrr_susceptibility.geojson`
- `data/raw/nerdrr_susceptibility.manifest.json`
- `data/interim/nerdrr_event_susceptibility.csv`

The official classes are preserved as `Very Low`, `Low`, `Moderate`, `High`,
and `Very High`; `gridcode / 5` is only a normalized modeling value. The layer
covers one Shillong-Silchar-Aizawl corridor, so unmatched events are expected.
The joined file remains incomplete until real rainfall, soil-moisture, and
slope values are added.

## Automatically collect public weather predictors

When direct NASA IMERG and SMAP downloads are difficult to obtain, collect a
transparent public fallback from ERA5-Land through Open-Meteo:

```powershell
python -m scripts.collect_weather_predictors
```

This creates 30 days of pre-event daily rainfall and 0-7 cm wetness values for
the dated field events. It does not use event-day or future values. The source
is explicitly labeled `ERA5_LAND_REANALYSIS_VIA_OPEN_METEO`, not satellite
observation. The rows remain `label_coverage=INCOMPLETE` until slope and
susceptibility are joined from the GIS workflow. Use `--limit 5` first to
check connectivity, then omit the limit for the full collection.

To remove only explicitly seeded demo records from Supabase and import the
collected source observations and event locations:

```powershell
python -m scripts.purge_demo_data
python -m scripts.import_weather_to_db
```

The imported locations intentionally have no risk assessment until verified
terrain, susceptibility, and weather coverage are joined. The frontend shows
the real conditions and `ASSESSMENT UNAVAILABLE` instead of inventing a score.

## Use the official GSI susceptibility export

GSI's current access route is the National Geoscience Data Repository (NGDR):

```text
https://geodataindia.gov.in/guestuser
```

The Northeast layers include Assam, Manipur/Nagaland, Meghalaya,
Mizoram/Tripura, and Sikkim susceptibility. Register through NGDR and
download the relevant layer as GeoJSON or Shapefile. Then validate a GeoJSON
export with:

```powershell
python -m scripts.import_gsi_susceptibility path\to\gsi_export.geojson
```

The importer records class counts, Northeast coverage, missing classes,
source, portal, and limitations. It does not guess class meanings from
unknown attribute names and does not treat the GSI layer as both a predictor
and a label.

## Derived GIS susceptibility proxy

If official GSI downloads are unavailable, build a clearly labeled proxy from
real rasters:

```powershell
python -m scripts.build_gis_proxy `
  --dem data\raw\gis\copernicus_dem.tif `
  --landcover data\raw\gis\landcover_risk_score.tif `
  --soil data\raw\gis\soil_risk_score.tif
```

The DEM is required. The optional layers are recommended; rows without all
three values are marked `label_coverage=INCOMPLETE` and must not enter the
training join. The optional rasters must already contain documented scores
from 0 to 1; raw categorical WorldCover or raw soil-property rasters must not
be treated as continuous risk scores. The result is not an official
susceptibility map. It uses an equal mean of normalized slope, land-cover,
and soil components and records the source paths and method in the command
output.

The preparation command clips downloaded rasters to the Northeast bounding
box and creates the score rasters:

```powershell
python -m scripts.prepare_gis_sources `
  --dem data\raw\downloads\copernicus_dem.tif `
  --worldcover data\raw\downloads\worldcover.tif `
  --soil data\raw\downloads\soil_property.tif `
  --soil-min 0 `
  --soil-max 100
```

The soil bounds must match the selected SoilGrids property and its units; do
not use `0` and `100` blindly. The manifest records the chosen bounds and
WorldCover mapping for review.

## Existing models worth evaluating

- The repository's deterministic operational index is the current baseline.
  It is explainable and remains the production fallback.
- NASA LHASA is a useful operational benchmark and possible input feature for
  rainfall-triggered warning. Its output must not be treated as independent
  ground truth.
- Landslide4Sense is useful for experimenting with satellite-image
  segmentation, but its benchmark patches are not a replacement for
  georeferenced Northeast India labels.
- Prithvi-EO and the Landslide4Sense U-Net baseline can be considered later
  for image segmentation after event polygons and imagery are available.

Do not fine-tune or deploy an external model until its input bands, license,
geographic coverage, label definition, and evaluation split are documented.
