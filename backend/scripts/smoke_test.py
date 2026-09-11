"""Read-only smoke test for a deployed or local backend."""

import os
import sys

import httpx


def main() -> int:
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    paths = [
        "/api/health",
        "/api/locations",
        "/api/risk/DEMO-EAST-KAMENG",
        "/api/alerts",
        "/api/incidents",
        "/api/field-reports",
        "/api/ingestion/observations",
        "/api/features/DEMO-EAST-KAMENG",
        "/api/impact/DEMO-EAST-KAMENG",
        "/api/priority",
        "/api/map/risk-zones",
    ]
    with httpx.Client(base_url=base_url, timeout=20) as client:
        for path in paths:
            response = client.get(path)
            if response.status_code >= 400:
                print(f"FAIL {path}: {response.status_code} {response.text[:200]}")
                return 1
            print(f"OK   {path}: {response.status_code}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
