from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.impact import ImpactResponse, PriorityResponse, RiskZoneResponse
from app.services.impact import get_impact, list_priority, list_risk_zones

router = APIRouter(tags=["impact"])


@router.get("/impact/{location_id}", response_model=ImpactResponse)
def get_location_impact(
    location_id: str,
    radius_km: float = Query(default=25, gt=0, le=100),
    db: Session = Depends(get_db),
) -> ImpactResponse:
    result = get_impact(db, location_id, radius_km)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={
            "code": "LOCATION_NOT_FOUND",
            "message": "The requested location does not exist.",
        })
    return result


@router.get("/priority", response_model=PriorityResponse)
def get_priority(db: Session = Depends(get_db)) -> PriorityResponse:
    return PriorityResponse(items=list_priority(db))


@router.get("/map/risk-zones", response_model=RiskZoneResponse)
def get_risk_zones(db: Session = Depends(get_db)) -> RiskZoneResponse:
    return RiskZoneResponse(zones=list_risk_zones(db))
