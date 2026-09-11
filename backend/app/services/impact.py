from math import asin, cos, radians, sin, sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InfrastructureAsset, Location, RiskAssessment
from app.schemas.impact import ExposedAsset, ImpactResponse, PriorityItem, RiskZone


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    value = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return earth_radius * 2 * asin(sqrt(value))


def get_impact(db: Session, location_id: str, radius_km: float = 25.0) -> ImpactResponse | None:
    location = db.get(Location, location_id)
    if location is None:
        return None
    assets = list(db.scalars(select(InfrastructureAsset)).all())
    exposed: list[ExposedAsset] = []
    for asset in assets:
        distance = distance_km(location.latitude, location.longitude, asset.latitude, asset.longitude)
        if distance <= radius_km:
            exposed.append(ExposedAsset(
                id=asset.id,
                name=asset.name,
                asset_type=asset.asset_type.value,
                distance_km=round(distance, 2),
                importance=asset.importance,
                is_demo=asset.is_demo,
            ))
    counts = {asset_type: sum(item.asset_type.value == asset_type for item in exposed)
              for asset_type in ("ROAD", "VILLAGE", "BRIDGE", "CRITICAL_ASSET")}
    return ImpactResponse(
        location_id=location_id,
        radius_km=radius_km,
        potentially_exposed=exposed,
        counts=counts,
        data_provenance="DEMO" if any(item.is_demo for item in exposed) else "REAL",
    )


def list_priority(db: Session) -> list[PriorityItem]:
    assessments = list(db.scalars(
        select(RiskAssessment).order_by(RiskAssessment.score.desc())
    ).all())
    items = []
    for assessment in assessments:
        impact = get_impact(db, assessment.location_id)
        count = len(impact.potentially_exposed) if impact else 0
        items.append(PriorityItem(
            location_id=assessment.location_id,
            score=assessment.score,
            priority="P1" if assessment.score >= 75 or count >= 5 else
            "P2" if assessment.score >= 50 or count >= 3 else
            "P3" if assessment.score >= 25 else "P4",
            exposed_asset_count=count,
            data_provenance="DEMO" if impact and impact.data_provenance == "DEMO" else "REAL",
        ))
    return items


def list_risk_zones(db: Session) -> list[RiskZone]:
    rows = list(db.execute(
        select(RiskAssessment, Location)
        .join(Location, Location.id == RiskAssessment.location_id)
        .order_by(RiskAssessment.score.desc())
    ).all())
    return [
        RiskZone(
            location_id=location.id,
            score=assessment.score,
            level=assessment.level.value,
            lat=location.latitude,
            lon=location.longitude,
            data_provenance="DEMO" if location.id.startswith("DEMO-") else "REAL",
        )
        for assessment, location in rows
    ]
