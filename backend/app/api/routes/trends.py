from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.trends import RiskTrendResponse
from app.services.trends import get_risk_trend

router = APIRouter(tags=["trends"])


@router.get("/trends/{location_id}", response_model=RiskTrendResponse)
def get_location_trend(
    location_id: str,
    db: Session = Depends(get_db),
) -> RiskTrendResponse:
    result = get_risk_trend(db, location_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "LOCATION_NOT_FOUND",
                "message": "The requested location does not exist.",
            },
        )
    return result
