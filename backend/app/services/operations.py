from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AlertStatus,
    FieldReport,
    FieldInspection,
    Incident,
    IncidentEvent,
    IncidentStatus,
    Priority,
)
from app.schemas.operations import FieldInspectionCreate, FieldReportCreate


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
    db.add(Alert(
        location_id=report.location_id,
        severity="HIGH",
        hazard="LANDSLIDE",
        reason="FIELD_REPORT_REQUIRES_INSPECTION",
        action="SDMA inspection required before response decision",
    ))
    db.commit()
    db.refresh(item)
    return item


def inspect_field_report(
    db: Session, report: FieldReport, payload: FieldInspectionCreate
) -> FieldInspection:
    inspection = report.inspection
    if inspection is None:
        inspection = FieldInspection(report_id=report.id)
        db.add(inspection)
    inspection.inspector = payload.inspector
    inspection.outcome = payload.outcome
    inspection.findings = payload.findings
    inspection.follow_up_action = payload.follow_up_action

    incident = db.scalar(
        select(Incident).where(Incident.location_id == report.location_id)
        .order_by(Incident.created_at.desc())
    )
    if incident is None:
        incident = Incident(
            location_id=report.location_id,
            priority=Priority.P1 if payload.outcome == "CONFIRMED_DISASTER" else Priority.P3,
            status=IncidentStatus.VERIFIED if payload.outcome == "CONFIRMED_DISASTER" else IncidentStatus.RESOLVED,
            summary=f"SDMA inspection for field report {report.id}",
        )
        db.add(incident)
        db.flush()
    else:
        incident.status = (
            IncidentStatus.VERIFIED
            if payload.outcome == "CONFIRMED_DISASTER"
            else IncidentStatus.RESOLVED
        )
        if payload.outcome == "CONFIRMED_DISASTER":
            incident.priority = Priority.P1
    db.add(IncidentEvent(
        incident_id=incident.id,
        status=incident.status,
        note=f"{payload.outcome}: {payload.findings}. Follow-up: {payload.follow_up_action}",
    ))
    db.commit()
    db.refresh(inspection)
    return inspection
