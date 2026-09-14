from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.satellite import (
    SatelliteObservationCreate,
    SatelliteObservationListResponse,
    SatelliteObservationResponse,
    SatelliteDetectionListResponse,
)
from app.services.satellite import create_satellite_observation, get_satellite_detections, list_satellite_observations

router = APIRouter(prefix="/satellite", tags=["satellite-evidence"])


@router.post(
    "/observations",
    response_model=SatelliteObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_satellite_observation(
    payload: SatelliteObservationCreate,
    db: Session = Depends(get_db),
) -> SatelliteObservationResponse:
    if not payload.is_demo and payload.platform.upper().startswith("DEMO"):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "SOURCE_LABEL_MISMATCH",
                "message": "Demo satellite platforms must be marked with is_demo=true.",
            },
        )
    return create_satellite_observation(db, payload)


@router.get("/observations", response_model=SatelliteObservationListResponse)
def get_satellite_observations(
    location_id: str | None = Query(default=None, max_length=64),
    db: Session = Depends(get_db),
) -> SatelliteObservationListResponse:
    return SatelliteObservationListResponse(
        observations=list_satellite_observations(db, location_id)
    )


@router.get("/{location_id}", response_model=SatelliteDetectionListResponse)
def get_satellite_detections_by_location(
    location_id: str, db: Session = Depends(get_db)
) -> SatelliteDetectionListResponse:
    location, detections = get_satellite_detections(db, location_id)
    if location is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "LOCATION_NOT_FOUND", "message": "The requested location does not exist."},
        )
    simulated = any(item["is_simulated"] for item in detections)
    return SatelliteDetectionListResponse(
        location={"id": location.id, "name": location.name},
        detections=detections,
        data_status="DEMO" if simulated else "LIVE",
        is_simulated=simulated,
    )
