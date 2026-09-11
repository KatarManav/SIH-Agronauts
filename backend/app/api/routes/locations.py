from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.locations import LocationListResponse
from app.services.risk import list_locations

router = APIRouter(tags=["locations"])


@router.get("/locations", response_model=LocationListResponse)
def get_locations(db: Session = Depends(get_db)) -> LocationListResponse:
    return LocationListResponse(
        locations=[{"id": item.id, "name": item.name, "latitude": item.latitude, "longitude": item.longitude}
                   for item in list_locations(db)]
    )
