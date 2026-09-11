from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EnvironmentalObservation
from app.schemas.features import FeatureVector


def build_feature_vector(db: Session, location_id: str) -> FeatureVector:
    observations = list(db.scalars(
        select(EnvironmentalObservation)
        .where(EnvironmentalObservation.location_id == location_id)
        .order_by(EnvironmentalObservation.observed_at.desc())
        .limit(100)
    ).all())
    values: dict[str, float] = {}
    source_ids: list[str] = []
    for observation in observations:
        source_ids.append(str(observation.id))
        for key, value in observation.values.items():
            if isinstance(value, (int, float)) and key not in values:
                values[key] = float(value)

    return FeatureVector(
        location_id=location_id,
        rainfall_mm=values.get("rainfall_mm"),
        soil_moisture_ratio=values.get("soil_moisture_ratio"),
        slope_degrees=values.get("slope_degrees"),
        susceptibility_index=values.get("susceptibility_index"),
        source_observation_ids=source_ids,
    )
