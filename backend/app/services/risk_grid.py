from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Location
from app.schemas.risk_grid import H3RiskCell, H3RiskFactor, RiskGridLocation, RiskGridResponse
from app.services.impact import list_risk_zones


def get_risk_grid(db: Session, location_query: str | None = None) -> RiskGridResponse:
    selected = None
    if location_query:
        normalized_query = location_query.strip().lower()
        selected = db.scalar(
            select(Location).where(
                (func.lower(Location.id) == normalized_query)
                | (func.lower(Location.name).contains(normalized_query))
                | (func.lower(Location.id).contains(normalized_query))
            )
        )
        if selected is None:
            return None

    zones = list_risk_zones(db)
    if selected:
        zones = [zone for zone in zones if zone.location_id == selected.id]

    cells = [
        H3RiskCell(
            h3Cell=zone.h3_cell,
            boundary=zone.h3_boundary,
            riskScore=zone.score,
            riskLevel=zone.level,
            trend=zone.trend,
            factors=[
                H3RiskFactor(
                    name=factor["name"],
                    impact=factor["contribution"] or "UNKNOWN",
                    value=factor["value"],
                    unit=factor["unit"],
                )
                for factor in zone.factors
            ],
            priority=zone.priority,
            impactCounts=zone.impact_counts,
            dataStatus=zone.data_provenance,
            satelliteEvidence=zone.satellite_evidence,
        )
        for zone in zones
    ]
    location = (
        RiskGridLocation(
            id=selected.id,
            name=selected.name,
            center={"lat": selected.latitude, "lon": selected.longitude},
        )
        if selected
        else None
    )
    return RiskGridResponse(location=location, cells=cells)
