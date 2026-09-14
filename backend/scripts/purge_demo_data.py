"""Remove records explicitly marked as demo or using DEMO identifiers."""

from sqlalchemy import delete, or_, select

from app.db.session import SessionLocal
from app.models import (
    Alert,
    EnvironmentalObservation,
    FieldReport,
    FieldInspection,
    Incident,
    IncidentEvent,
    InfrastructureAsset,
    Location,
    ResponseAction,
    RiskAssessment,
    RiskFactor,
    SatelliteObservation,
)


def purge() -> dict[str, int]:
    counts = {}
    with SessionLocal.begin() as db:
        demo_locations = db.scalars(
            select(Location).where(Location.id.ilike("DEMO%"))
        ).all()
        location_ids = [item.id for item in demo_locations]

        for model, column in (
            (EnvironmentalObservation, EnvironmentalObservation.is_demo),
            (InfrastructureAsset, InfrastructureAsset.is_demo),
            (SatelliteObservation, SatelliteObservation.is_demo),
        ):
            result = db.execute(delete(model).where(
                or_(column.is_(True), model.location_id.in_(location_ids))
            ))
            counts[model.__tablename__] = result.rowcount

        for model in (FieldReport, Alert, Incident, RiskAssessment):
            if model is FieldReport:
                db.execute(delete(FieldInspection).where(
                    FieldInspection.report_id.in_(
                        select(FieldReport.id).where(FieldReport.location_id.in_(location_ids))
                    )
                ))
            if model is Incident:
                db.execute(delete(IncidentEvent).where(
                    IncidentEvent.incident_id.in_(
                        select(Incident.id).where(Incident.location_id.in_(location_ids))
                    )
                ))
                db.execute(delete(ResponseAction).where(
                    ResponseAction.incident_id.in_(
                        select(Incident.id).where(Incident.location_id.in_(location_ids))
                    )
                ))
            if model is RiskAssessment:
                db.execute(delete(RiskFactor).where(
                    RiskFactor.assessment_id.in_(
                        select(RiskAssessment.id).where(RiskAssessment.location_id.in_(location_ids))
                    )
                ))
            result = db.execute(delete(model).where(model.location_id.in_(location_ids)))
            counts[model.__tablename__] = result.rowcount

        if location_ids:
            result = db.execute(delete(Location).where(Location.id.in_(location_ids)))
            counts["locations"] = result.rowcount
        else:
            counts["locations"] = 0
    return counts


if __name__ == "__main__":
    print(purge())
