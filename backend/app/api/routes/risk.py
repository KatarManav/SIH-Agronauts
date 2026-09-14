from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import Priority
from app.schemas.risk import ImpactSummary, RiskResponse
from app.services.impact import get_impact
from app.services.risk import get_location_risk
from app.schemas.risk_grid import RiskGridResponse
from app.services.risk_grid import get_risk_grid

router = APIRouter(tags=["risk"])


@router.get("/risk/grid", response_model=RiskGridResponse)
def get_grid(
    location: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
) -> RiskGridResponse:
    result = get_risk_grid(db, location)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "LOCATION_NOT_FOUND", "message": "The requested location does not exist."},
        )
    return result


@router.get("/risk/{location_id}", response_model=RiskResponse)
def get_risk(location_id: str, db: Session = Depends(get_db)) -> RiskResponse:
    result = get_location_risk(db, location_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "LOCATION_NOT_FOUND", "message": "The requested location does not exist."},
        )

    location, assessment = result
    if assessment is None:
        return RiskResponse(
            location={
                "id": location.id,
                "name": location.name,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            risk={"score": 0, "level": "UNKNOWN", "trend": "UNKNOWN"},
            factors=[],
            impact=ImpactSummary(),
            priority=Priority.P4,
        )

    impact = get_impact(db, location_id)
    impact_counts = impact.counts if impact else {}
    return RiskResponse(
        location={
            "id": location.id,
            "name": location.name,
            "latitude": location.latitude,
            "longitude": location.longitude,
        },
        risk={"score": assessment.score, "level": assessment.level, "trend": assessment.trend},
        factors=[
            {
                "name": factor.name,
                "value": factor.value,
                "unit": factor.unit,
                "contribution": factor.contribution,
                "direction": factor.direction,
            }
            for factor in assessment.factors
        ],
        impact=ImpactSummary(
            roads=impact_counts.get("ROAD", 0),
            villages=impact_counts.get("VILLAGE", 0),
            bridges=impact_counts.get("BRIDGE", 0),
            critical_assets=impact_counts.get("CRITICAL_ASSET", 0),
        ),
        priority=Priority.P1 if assessment.score >= 75 else
        Priority.P2 if assessment.score >= 50 else
        Priority.P3 if assessment.score >= 25 else Priority.P4,
    )
