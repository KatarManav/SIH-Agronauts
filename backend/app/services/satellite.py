import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Location, SatelliteObservation
from app.schemas.satellite import SatelliteObservationCreate


def _response(item: SatelliteObservation, location: Location | None = None) -> dict:
    now = datetime.now(timezone.utc)
    acquisition = item.acquisition_at
    if acquisition.tzinfo is None:
        acquisition = acquisition.replace(tzinfo=timezone.utc)
    evidence = json.loads(item.evidence_json)
    confidence = evidence.get("confidence")
    if isinstance(confidence, float | int):
        confidence = float(confidence * 100 if confidence <= 1 else confidence)
    return {
        "id": item.id,
        "location_id": item.location_id,
        "platform": item.platform,
        "product_type": item.product_type,
        "acquisition_at": item.acquisition_at,
        "processed_at": item.processed_at,
        "processing_quality": item.processing_quality,
        "change_detected": item.change_detected,
        "evidence": evidence,
        "is_demo": item.is_demo,
        "freshness_hours": round((now - acquisition).total_seconds() / 3600, 2),
        "latitude": location.latitude if location else evidence.get("latitude", 0),
        "longitude": location.longitude if location else evidence.get("longitude", 0),
        "detection_type": str(evidence.get("detection_type", item.product_type)),
        "confidence": confidence,
        "detected_at": item.acquisition_at,
        "data_status": "DEMO" if item.is_demo else "LIVE",
        "is_simulated": item.is_demo,
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
    return _response(item, db.get(Location, item.location_id))


def list_satellite_observations(
    db: Session, location_id: str | None = None
) -> list[dict]:
    query = select(SatelliteObservation).order_by(
        SatelliteObservation.acquisition_at.desc()
    )
    if location_id:
        query = query.where(SatelliteObservation.location_id == location_id)
    items = db.scalars(query.limit(100)).all()
    locations = {
        location.id: location
        for location in db.scalars(select(Location).where(Location.id.in_({item.location_id for item in items}))).all()
    } if items else {}
    return [_response(item, locations.get(item.location_id)) for item in items]


def get_satellite_detections(db: Session, location_id: str) -> tuple[Location | None, list[dict]]:
    location = db.get(Location, location_id)
    if location is None:
        return None, []
    return location, list_satellite_observations(db, location_id)
