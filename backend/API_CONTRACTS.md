# Frontend API contracts

For the current local setup, set the frontend base URL once:

```env
VITE_API_BASE_URL=http://localhost:8000
```

The frontend calls FastAPI directly during local development. Keep response
handling in an API client so the base URL can be changed without changing
components.

## Read endpoints

| Use case | Endpoint |
| --- | --- |
| Backend status | `GET /api/health` |
| Location selector/map | `GET /api/locations` |
| Location risk card | `GET /api/risk/{location_id}` |
| Exposed assets | `GET /api/impact/{location_id}?radius_km=25` |
| Response queue | `GET /api/priority` |
| Risk map | `GET /api/map/risk-zones` |
| H3 risk grid | `GET /api/risk/grid?location=East%20Kameng` |
| Satellite detections | `GET /api/satellite/{location_id}` |

H3 grid cells and `/api/map/risk-zones` now include `satelliteEvidence`.
Satellite evidence is attached to the H3 cell for the associated location and
includes coordinates, detection type, timestamp, data status, and whether the
record is simulated. A change signal is not a confirmed landslide.
| Alerts | `GET /api/alerts` |
| Incident list | `GET /api/incidents` |
| Incident timeline | `GET /api/incidents/{incident_id}/timeline` |
| Field reports | `GET /api/field-reports` |
| Environmental observations | `GET /api/ingestion/observations?location_id=...` |
| Satellite evidence | `GET /api/satellite/observations?location_id=...` |
| Risk history | `GET /api/trends/{location_id}` |

Satellite evidence can be submitted through:

```text
POST /api/satellite/observations
```

The request records acquisition time, processing quality, change detection,
evidence metadata, and demo provenance. Platforms whose names start with
`DEMO` must set `is_demo` to `true`. The response includes `freshness_hours`;
this is evidence freshness, not a live prediction.

Risk history returns up to the latest 100 persisted assessments in
chronological order:

```json
{
  "location_id": "DEMO-EAST-KAMENG",
  "points": [
    {
      "assessed_at": "2026-09-11T12:00:00Z",
      "score": 87,
      "level": "CRITICAL",
      "trend": "RISING"
    }
  ],
  "data_provenance": "Backend risk assessment history; demo records are labeled by location."
}
```

## Risk response

`GET /api/risk/{location_id}` returns:

```json
{
  "location": {
    "id": "DEMO-EAST-KAMENG",
    "name": "East Kameng (DEMO)",
    "lat": 27.264,
    "lon": 92.425
  },
  "risk": {
    "score": 87,
    "level": "CRITICAL",
    "trend": "RISING"
  },
  "factors": [
    {
      "name": "Rainfall",
      "value": 142,
      "unit": "mm",
      "contribution": "HIGH",
      "direction": "INCREASES_RISK"
    }
  ],
  "impact": {
    "roads": 0,
    "villages": 0,
    "bridges": 0,
    "critical_assets": 0
  },
  "priority": "P1"
}
```

The `DEMO` suffix and provenance fields identify simulated data. The frontend must not describe it as a live forecast.

## Mutating endpoints

```text
POST /api/alerts/{alert_id}/acknowledge
{"acknowledged_by": "operator-id"}

POST /api/alerts/{alert_id}/assign
{"assigned_to": "district-response-team"}

POST /api/alerts/{alert_id}/escalate
{"reason": "Operational response window exceeded."}

POST /api/field-reports
{
  "location_id": "DEMO-EAST-KAMENG",
  "observation": "Fresh cracks observed on hillside.",
  "reporter_type": "FIELD_TEAM",
  "photo_path": null
}
```

Use the deployed `/docs` page as the authoritative generated schema reference.
