# LandslideGuard Node.js API Gateway

The gateway is the public frontend-facing API. It forwards `/api/*` requests to the existing FastAPI service and does not duplicate ML, GIS, or database logic.

## Local setup

1. Copy `.env.example` to `.env`.
2. Set `FASTAPI_URL=http://localhost:8000`.
3. Install dependencies with `npm install`.
4. Start FastAPI on port 8000.
5. Start the gateway with `npm run dev`.

The public API is available at `http://localhost:3000`. Configure the React frontend with:

```env
VITE_API_BASE_URL=http://localhost:3000
```

The gateway health response includes the FastAPI health response:

```text
GET /api/health
```

## Production

Deploy the gateway container with `FASTAPI_URL` pointing to the private or HTTPS FastAPI service and set `CORS_ORIGINS` to the deployed frontend origin. The gateway returns controlled errors for FastAPI timeouts and unavailable services.
