import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SatelliteObservation
from app.schemas.satellite import SatelliteObservationCreate


def _response(item: SatelliteObservation) -> dict:
    now = datetime.now(timezone.utc)
    acquisition = item.acquisition_at
    if acquisition.tzinfo is None:
        acquisition = acquisition.replace(tzinfo=timezone.utc)
    return {
        "id": item.id,
        "location_id": item.location_id,
        "platform": item.platform,
        "product_type": item.product_type,
        "acquisition_at": item.acquisition_at,
        "processed_at": item.processed_at,
        "processing_quality": item.processing_quality,
        "change_detected": item.change_detected,
        "evidence": json.loads(item.evidence_json),
        "is_demo": item.is_demo,
        "freshness_hours": round((now - acquisition).total_seconds() / 3600, 2),
    }


def create_satellite_observation(
    db: Session, payload: SatelliteObservationCreate
) -> dict:
    item = SatelliteObservation(
        location_id=payload.location_id,
        platform=payload.platform,
        product_type=payload.product_type,
        acquisition_at=payload.acquisition_at,
        processing_quality=payload.processing_quality,
        change_detected=payload.change_detected,
        evidence_json=json.dumps(payload.evidence),
        is_demo=payload.is_demo,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _response(item)


def list_satellite_observations(
    db: Session, location_id: str | None = None
) -> list[dict]:
    query = select(SatelliteObservation).order_by(
        SatelliteObservation.acquisition_at.desc()
    )
    if location_id:
        query = query.where(SatelliteObservation.location_id == location_id)
    return [_response(item) for item in db.scalars(query.limit(100)).all()]
