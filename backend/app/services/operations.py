from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AlertStatus,
    FieldReport,
    Incident,
    IncidentEvent,
    IncidentStatus,
    Priority,
)
from app.schemas.operations import FieldReportCreate


def list_alerts(db: Session) -> list[Alert]:
    return list(db.scalars(select(Alert).order_by(Alert.created_at.desc())).all())


def get_alert(db: Session, alert_id: UUID) -> Alert | None:
    return db.get(Alert, alert_id)


def acknowledge_alert(db: Session, alert: Alert, acknowledged_by: str) -> Alert:
    alert.status = AlertStatus.ACKNOWLEDGED
    incident = db.scalar(
        select(Incident).where(Incident.location_id == alert.location_id).order_by(Incident.created_at.desc())
    )
    if incident is not None:
        incident.status = IncidentStatus.ACKNOWLEDGED
        db.add(IncidentEvent(
            incident_id=incident.id,
            status=IncidentStatus.ACKNOWLEDGED,
            note=f"Acknowledged by {acknowledged_by}",
        ))
    db.commit()
    db.refresh(alert)
    return alert


def assign_alert(db: Session, alert: Alert, assigned_to: str) -> Alert:
    incident = db.scalar(
        select(Incident).where(Incident.location_id == alert.location_id).order_by(Incident.created_at.desc())
    )
    if incident is None:
        incident = Incident(
            location_id=alert.location_id,
            priority=Priority.P1 if alert.severity.upper() == "CRITICAL" else Priority.P2,
            status=IncidentStatus.ASSIGNED,
            summary=f"Operational response for alert {alert.id}",
        )
        db.add(incident)
        db.flush()
    else:
        incident.status = IncidentStatus.ASSIGNED
    db.add(IncidentEvent(
        incident_id=incident.id,
        status=IncidentStatus.ASSIGNED,
        note=f"Assigned to {assigned_to}",
    ))
    db.commit()
    db.refresh(alert)
    return alert


def escalate_alert(db: Session, alert: Alert, reason: str) -> Alert:
    alert.status = AlertStatus.ACTIVE
    incident = db.scalar(
        select(Incident).where(Incident.location_id == alert.location_id).order_by(Incident.created_at.desc())
    )
    if incident is None:
        incident = Incident(
            location_id=alert.location_id,
            priority=Priority.P1,
            status=IncidentStatus.ESCALATED,
            summary=f"Escalated response for alert {alert.id}",
        )
        db.add(incident)
        db.flush()
    else:
        incident.priority = Priority.P1
        incident.status = IncidentStatus.ESCALATED
    db.add(IncidentEvent(incident_id=incident.id, status=IncidentStatus.ESCALATED, note=reason))
    db.commit()
    db.refresh(alert)
    return alert


def list_incidents(db: Session) -> list[Incident]:
    return list(db.scalars(select(Incident).order_by(Incident.created_at.desc())).all())


def get_incident(db: Session, incident_id: UUID) -> Incident | None:
    return db.get(Incident, incident_id)


def list_incident_events(db: Session, incident_id: UUID) -> list[IncidentEvent]:
    return list(db.scalars(
        select(IncidentEvent)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.created_at)
    ).all())


def list_field_reports(db: Session) -> list[FieldReport]:
    return list(db.scalars(select(FieldReport).order_by(FieldReport.reported_at.desc())).all())


def create_field_report(db: Session, report: FieldReportCreate) -> FieldReport:
    item = FieldReport(**report.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
