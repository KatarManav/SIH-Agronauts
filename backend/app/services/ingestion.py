import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EnvironmentalObservation
from app.schemas.ingestion import EnvironmentalObservationCreate


def create_observation(
    db: Session, payload: EnvironmentalObservationCreate
) -> EnvironmentalObservation:
    item = EnvironmentalObservation(
        location_id=payload.location_id,
        source=payload.source,
        data_class=payload.data_class,
        observed_at=payload.observed_at,
        values_json=json.dumps(payload.values),
        is_demo=payload.is_demo,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_observations(db: Session, location_id: str | None = None) -> list[EnvironmentalObservation]:
    query = select(EnvironmentalObservation).order_by(EnvironmentalObservation.observed_at.desc())
    if location_id:
        query = query.where(EnvironmentalObservation.location_id == location_id)
    return list(db.scalars(query.limit(100)).all())
