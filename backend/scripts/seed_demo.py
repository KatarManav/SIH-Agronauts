"""Seed clearly labeled pilot data for frontend and judge demonstrations."""

import uuid

from app.db.session import SessionLocal
from app.models import (
    Alert,
    AlertStatus,
    Incident,
    IncidentEvent,
    IncidentStatus,
    Location,
    Priority,
    RiskAssessment,
    RiskFactor,
    RiskLevel,
    RiskTrend,
    AssetType,
    InfrastructureAsset,
)
from sqlalchemy import select


DEMO_LOCATIONS = [
    {
        "id": "DEMO-EAST-KAMENG",
        "name": "East Kameng (DEMO)",
        "latitude": 27.264,
        "longitude": 92.425,
        "score": 87,
        "level": RiskLevel.CRITICAL,
        "trend": RiskTrend.RISING,
        "factors": [
            ("Rainfall", 142, "mm", "HIGH"),
            ("Soil Moisture", 0.81, "ratio", "HIGH"),
            ("Slope", 31, "degrees", "MEDIUM"),
        ],
    },
    {
        "id": "DEMO-SIKKIM-NORTH",
        "name": "North Sikkim (DEMO)",
        "latitude": 27.988,
        "longitude": 88.755,
        "score": 61,
        "level": RiskLevel.HIGH,
        "trend": RiskTrend.RISING,
        "factors": [
            ("Rainfall", 96, "mm", "HIGH"),
            ("Soil Moisture", 0.67, "ratio", "MEDIUM"),
            ("Slope", 28, "degrees", "MEDIUM"),
        ],
    },
]


def seed_demo_data() -> None:
    with SessionLocal.begin() as db:
        for item in DEMO_LOCATIONS:
            location = db.get(Location, item["id"])
            if location is None:
                location = Location(
                    id=item["id"],
                    name=item["name"],
                    latitude=item["latitude"],
                    longitude=item["longitude"],
                )
                db.add(location)
                db.flush()

            assessment = RiskAssessment(
                location_id=location.id,
                score=item["score"],
                level=item["level"],
                trend=item["trend"],
            )
            assessment.factors = [
                RiskFactor(
                    name=name,
                    value=value,
                    unit=unit,
                    contribution=contribution,
                    direction="INCREASES_RISK",
                )
                for name, value, unit, contribution in item["factors"]
            ]
            db.add(assessment)

            if item["score"] >= 75:
                alert = db.scalar(
                    select(Alert).where(
                        Alert.location_id == location.id,
                        Alert.reason == "DEMO_HEAVY_RAINFALL",
                    )
                )
                if alert is None:
                    db.add(Alert(
                        location_id=location.id,
                        severity="CRITICAL",
                        hazard="LANDSLIDE",
                        reason="DEMO_HEAVY_RAINFALL",
                        action="AVOID_HILLSIDE_ROAD",
                        status=AlertStatus.ACTIVE,
                    ))

                incident = db.scalar(
                    select(Incident).where(
                        Incident.location_id == location.id,
                        Incident.summary == "DEMO response workflow",
                    )
                )
                if incident is None:
                    incident = Incident(
                        location_id=location.id,
                        priority=Priority.P1,
                        status=IncidentStatus.ALERT_GENERATED,
                        summary="DEMO response workflow",
                    )
                    db.add(incident)
                    db.flush()
                    db.add(IncidentEvent(
                        incident_id=incident.id,
                        status=IncidentStatus.ALERT_GENERATED,
                        note="Demo alert generated from simulated risk assessment.",
                    ))

            assets = [
                ("DEMO-EK-HIGHWAY-01", "East Kameng hillside road", AssetType.ROAD, 27.27, 92.43, 4),
                ("DEMO-EK-VILLAGE-01", "Pilot village", AssetType.VILLAGE, 27.28, 92.42, 3),
                ("DEMO-EK-BRIDGE-01", "River bridge", AssetType.BRIDGE, 27.26, 92.43, 5),
            ] if location.id == "DEMO-EAST-KAMENG" else [
                ("DEMO-NS-ROAD-01", "North Sikkim mountain road", AssetType.ROAD, 27.99, 88.76, 4),
                ("DEMO-NS-HOSPITAL-01", "Pilot health centre", AssetType.CRITICAL_ASSET, 27.98, 88.75, 5),
            ]
            for asset_id, name, asset_type, lat, lon, importance in assets:
                asset_uuid = uuid.uuid5(uuid.NAMESPACE_URL, asset_id)
                if db.get(InfrastructureAsset, asset_uuid):
                    continue
                db.add(InfrastructureAsset(
                    id=asset_uuid,
                    location_id=location.id,
                    name=name,
                    asset_type=asset_type,
                    latitude=lat,
                    longitude=lon,
                    importance=importance,
                    is_demo=True,
                ))


if __name__ == "__main__":
    seed_demo_data()
    print("Seeded DEMO pilot locations and risk assessments.")
