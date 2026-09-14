from math import asin, cos, radians, sin, sqrt

import h3
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import InfrastructureAsset, Location, RiskAssessment
from app.core.config import get_settings
from app.schemas.impact import (
    ExposedAsset, ImpactResponse, PriorityItem, RiskZone, SatelliteEvidence,
)
from app.services.satellite import list_satellite_observations


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
        select(RiskAssessment).order_by(
            RiskAssessment.assessed_at.desc(), RiskAssessment.score.desc()
        )
    ).all())
    latest_by_location: dict[str, RiskAssessment] = {}
    for assessment in assessments:
        latest_by_location.setdefault(assessment.location_id, assessment)
    items = []
    for assessment in sorted(
        latest_by_location.values(), key=lambda item: item.score, reverse=True
    ):
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
        .options(selectinload(RiskAssessment.factors))
        .join(Location, Location.id == RiskAssessment.location_id)
        .order_by(RiskAssessment.assessed_at.desc(), RiskAssessment.score.desc())
    ).all())
    latest_by_location: dict[str, tuple[RiskAssessment, Location]] = {}
    for assessment, location in rows:
        latest_by_location.setdefault(location.id, (assessment, location))
    satellite_by_location: dict[str, list[dict]] = {}
    for observation in list_satellite_observations(db):
        satellite_by_location.setdefault(observation["location_id"], []).append(observation)
    zones: list[RiskZone] = []
    for assessment, location in sorted(
        latest_by_location.values(), key=lambda item: item[0].score, reverse=True
    ):
        impact = get_impact(db, location.id)
        cell = h3.latlng_to_cell(
            location.latitude, location.longitude, get_settings().h3_resolution
        )
        boundary = [[lat, lon] for lat, lon in h3.cell_to_boundary(cell)]
        zones.append(RiskZone(
            location_id=location.id,
            score=assessment.score,
            level=assessment.level.value,
            lat=location.latitude,
            lon=location.longitude,
            h3_cell=cell,
            h3_boundary=boundary,
            trend=assessment.trend.value,
            priority=(
                "P1" if assessment.score >= 75 or len(impact.potentially_exposed) >= 5
                else "P2" if assessment.score >= 50 or len(impact.potentially_exposed) >= 3
                else "P3" if assessment.score >= 25 else "P4"
            ),
            impact_counts=impact.counts if impact else {},
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
            satelliteEvidence=[
                SatelliteEvidence(
                    id=observation["id"],
                    platform=observation["platform"],
                    product_type=observation["product_type"],
                    detection_type=observation["detection_type"],
                    confidence=observation["confidence"],
                    detected_at=observation["detected_at"].isoformat(),
                    latitude=observation["latitude"],
                    longitude=observation["longitude"],
                    change_detected=observation["change_detected"],
                    data_status=observation["data_status"],
                    is_simulated=observation["is_simulated"],
                )
                for observation in satellite_by_location.get(location.id, [])
            ],
            data_provenance="DEMO" if location.id.startswith("DEMO-") else "REAL",
        ))
    return zones
