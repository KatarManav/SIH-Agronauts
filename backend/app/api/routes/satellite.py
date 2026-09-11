from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.satellite import (
    SatelliteObservationCreate,
    SatelliteObservationListResponse,
    SatelliteObservationResponse,
)
from app.services.satellite import create_satellite_observation, list_satellite_observations

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
