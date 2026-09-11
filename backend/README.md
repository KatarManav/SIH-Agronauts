# LandslideGuard NER Backend

P0 is a modular FastAPI foundation for the LandslideGuard NER backend. It is API-first and intentionally does not claim to provide live risk predictions until the data and model phases are implemented.

## Local setup

1. Create a Supabase project.
2. In Supabase **SQL Editor**, run `supabase/001_enable_postgis.sql` from this repository.
3. Open **Connect → ORMs → SQLAlchemy**, copy the PostgreSQL URI, and replace its password.
4. Copy `.env.example` to `.env`.
5. Set `SUPABASE_DATABASE_URL` to that PostgreSQL URI. Do not use the `https://<project>.supabase.co` dashboard URL in this field. Use the pooler URI if the direct connection is not reachable.
6. Install dependencies with `python -m pip install -r requirements.txt`.
7. Start the API with `uvicorn app.main:app --reload`.

The API is available at `http://localhost:8000`, with OpenAPI at `/docs` and the database diagnostic at `/api/health`.

## Docker

```powershell
docker compose up --build
```

The container expects the same `.env` file and connects directly to Supabase. No database credentials are stored in the image.

## Environment variables

See `.env.example`. Production must set a real `SUPABASE_DATABASE_URL`, a restricted `CORS_ORIGINS` list containing the deployed frontend origin, and `APP_ENV=production`.

## Deployment

Deploy the `backend` directory as a container to a provider that supports public HTTPS services. Set the Supabase connection string and environment variables in the provider's secret configuration. Verify:

```text
GET https://<backend-host>/api/health
GET https://<backend-host>/docs
```

The response must show `status=ok` and `database=connected` before the frontend switches from mocks to the live API.

Production environment variables are documented in `.env.example`. Keep
`SUPABASE_DATABASE_URL` in the hosting provider's secret configuration and
allow only the deployed frontend origin in `CORS_ORIGINS`.

## Demo pilot data

The repository includes intentionally labeled `DEMO` locations for API and frontend integration. After enabling PostGIS and creating the schema, run:

```powershell
python -c "from app.db.init_db import create_tables; create_tables()"
python -m scripts.seed_demo
```

This data is simulated demonstration data, not a live environmental feed or a trained ML prediction. It must not be presented as a scientific forecast.

## Operational APIs

The current workflow endpoints are:

```text
GET  /api/alerts
GET  /api/alerts/{alert_id}
POST /api/alerts/{alert_id}/acknowledge
POST /api/alerts/{alert_id}/assign
POST /api/alerts/{alert_id}/escalate
GET  /api/incidents
GET  /api/incidents/{incident_id}
GET  /api/incidents/{incident_id}/timeline
GET  /api/field-reports
POST /api/field-reports
```

Alert state changes create incident timeline events. Field reports are stored as supporting evidence and do not retrain or silently modify the risk model.

## Normalized environmental ingestion

Environmental sources must enter through the normalized observation contract:

```text
POST /api/ingestion/observations
GET  /api/ingestion/observations?location_id=...
```

Each observation records its location, source, data class, timestamp, normalized values, and whether it is demo data. Source adapters must convert verified external feeds into this contract; no external provider is claimed to be live until an adapter is implemented and tested. `DEMO_*` sources are rejected unless `is_demo=true`.

## Feature engineering and risk engine

The current deterministic operational index is available through:

```text
GET  /api/features/{location_id}
POST /api/risk/{location_id}/calculate
```

The feature layer selects the latest numeric values by feature name. The risk engine currently weights rainfall, soil moisture, slope, and susceptibility into a bounded 0–100 operational index, returns structured factor contributions, calculates a trend against the previous assessment, and generates a threshold alert at `75`. This is not a calibrated probability and is not yet an XGBoost/SHAP model; the contract is designed so a validated ML engine can replace the calculation later.

## GIS impact and priority

The pilot GIS endpoints are:

```text
GET /api/impact/{location_id}?radius_km=25
GET /api/priority
GET /api/map/risk-zones
```

They report infrastructure as **potentially exposed**, not certain to fail. Current seeded assets are explicitly demo records; replace them with verified road, village, bridge, and critical-asset datasets before making real-world claims.

## Supabase setup verification

From the `backend` directory, run:

```powershell
python -c "from app.core.config import get_settings; from sqlalchemy import create_engine, text; e=create_engine(get_settings().database_url); print(e.connect().execute(text('SELECT 1')).scalar())"
```

The command should print `1`. If configuration fails with a PostgreSQL URI error, the Supabase project URL was entered instead of the database connection URI.

## Node.js gateway

The repository also contains a separate `gateway/` Express service. The frontend should call the gateway, not FastAPI directly:

```text
React → http://localhost:3000 → FastAPI http://localhost:8000
```

Start FastAPI first, then configure and start the gateway from `gateway/`. See `gateway/README.md`.

## Frontend integration smoke test

The read-only smoke test checks the complete frontend-facing API surface:

```powershell
$env:API_BASE_URL="http://localhost:8000"
python -m scripts.smoke_test
```

For a deployed service, set `API_BASE_URL` to its HTTPS URL. The script does not create or modify records.
