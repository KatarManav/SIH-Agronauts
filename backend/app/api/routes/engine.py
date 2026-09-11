from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.risk_engine import RiskCalculationResponse
from app.services.features import build_feature_vector
from app.services.risk_engine import calculate_risk, persist_risk
from app.services.risk import get_location_risk

router = APIRouter(tags=["risk-engine"])


@router.post("/risk/{location_id}/calculate", response_model=RiskCalculationResponse)
def calculate_location_risk(
    location_id: str, db: Session = Depends(get_db)
) -> RiskCalculationResponse:
    result = calculate_risk(db, location_id)
    if result is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "FEATURES_UNAVAILABLE",
                "message": "No numeric environmental observations are available for this location.",
            },
        )
    assessment = persist_risk(db, location_id, result)
    location_result = get_location_risk(db, location_id)
    if location_result is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    location, _ = location_result
    return RiskCalculationResponse(
        model_risk_type="DETERMINISTIC_OPERATIONAL_INDEX",
        risk={
            "location": {
                "id": location.id,
                "name": location.name,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "risk": {
                "score": assessment.score,
                "level": assessment.level,
                "trend": assessment.trend,
            },
            "factors": [
                {
                    "name": factor.name,
                    "value": factor.value,
                    "unit": factor.unit,
                    "contribution": factor.contribution,
                    "direction": factor.direction,
                }
                for factor in assessment.factors
            ],
            "priority": result.priority,
        },
    )


@router.get("/features/{location_id}")
def get_features(location_id: str, db: Session = Depends(get_db)):
    return build_feature_vector(db, location_id)
