from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Location, RiskAssessment
from app.schemas.trends import RiskTrendPoint, RiskTrendResponse


def get_risk_trend(db: Session, location_id: str) -> RiskTrendResponse | None:
    if db.scalar(select(Location.id).where(Location.id == location_id)) is None:
        return None

    assessments = db.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.location_id == location_id)
        .order_by(RiskAssessment.assessed_at.desc())
        .limit(100)
    ).all()
    points = [
        RiskTrendPoint(
            assessed_at=assessment.assessed_at,
            score=assessment.score,
            level=assessment.level,
            trend=assessment.trend,
        )
        for assessment in reversed(assessments)
    ]
    return RiskTrendResponse(
        location_id=location_id,
        points=points,
        data_provenance="Backend risk assessment history; demo records are labeled by location.",
    )
