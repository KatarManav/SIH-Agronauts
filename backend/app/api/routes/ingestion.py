from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ingestion import (
    EnvironmentalObservationCreate,
    EnvironmentalObservationListResponse,
    EnvironmentalObservationResponse,
)
from app.services.ingestion import create_observation, list_observations

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post(
    "/observations",
    response_model=EnvironmentalObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_observation(
    payload: EnvironmentalObservationCreate,
    db: Session = Depends(get_db),
) -> EnvironmentalObservationResponse:
    if not payload.is_demo and payload.source.upper().startswith("DEMO"):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "SOURCE_LABEL_MISMATCH",
                "message": "Demo sources must be explicitly marked with is_demo=true.",
            },
        )
    return create_observation(db, payload)


@router.get("/observations", response_model=EnvironmentalObservationListResponse)
def get_observations(
    location_id: str | None = Query(default=None, max_length=64),
    db: Session = Depends(get_db),
) -> EnvironmentalObservationListResponse:
    return EnvironmentalObservationListResponse(
        observations=list_observations(db, location_id)
    )
