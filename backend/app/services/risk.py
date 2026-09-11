from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Location, RiskAssessment


def list_locations(db: Session) -> list[Location]:
    return list(db.scalars(select(Location).order_by(Location.name)).all())


def get_location_risk(db: Session, location_id: str) -> tuple[Location, RiskAssessment | None] | None:
    location = db.get(Location, location_id)
    if location is None:
        return None

    assessment = db.scalar(
        select(RiskAssessment)
        .where(RiskAssessment.location_id == location_id)
        .options(joinedload(RiskAssessment.factors))
        .order_by(RiskAssessment.assessed_at.desc())
    )
    return location, assessment
