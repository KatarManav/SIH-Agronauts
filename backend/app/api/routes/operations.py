from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.operations import (
    AcknowledgeRequest,
    AlertListResponse,
    AlertResponse,
    AssignmentRequest,
    EscalationRequest,
    FieldReportCreate,
    FieldReportListResponse,
    FieldReportResponse,
    IncidentListResponse,
    IncidentResponse,
    IncidentTimelineResponse,
)
from app.services.operations import (
    acknowledge_alert,
    assign_alert,
    create_field_report,
    escalate_alert,
    get_alert,
    get_incident,
    list_alerts,
    list_field_reports,
    list_incident_events,
    list_incidents,
)

router = APIRouter(tags=["operations"])


def not_found(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": message})


@router.get("/alerts", response_model=AlertListResponse)
def get_alerts(db: Session = Depends(get_db)) -> AlertListResponse:
    return AlertListResponse(alerts=list_alerts(db))


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
def get_alert_by_id(alert_id: UUID, db: Session = Depends(get_db)) -> AlertResponse:
    alert = get_alert(db, alert_id)
    if alert is None:
        raise not_found("ALERT_NOT_FOUND", "The requested alert does not exist.")
    return alert


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge(alert_id: UUID, payload: AcknowledgeRequest, db: Session = Depends(get_db)) -> AlertResponse:
    alert = get_alert(db, alert_id)
    if alert is None:
        raise not_found("ALERT_NOT_FOUND", "The requested alert does not exist.")
    return acknowledge_alert(db, alert, payload.acknowledged_by)


@router.post("/alerts/{alert_id}/assign", response_model=AlertResponse)
def assign(alert_id: UUID, payload: AssignmentRequest, db: Session = Depends(get_db)) -> AlertResponse:
    alert = get_alert(db, alert_id)
    if alert is None:
        raise not_found("ALERT_NOT_FOUND", "The requested alert does not exist.")
    return assign_alert(db, alert, payload.assigned_to)


@router.post("/alerts/{alert_id}/escalate", response_model=AlertResponse)
def escalate(alert_id: UUID, payload: EscalationRequest, db: Session = Depends(get_db)) -> AlertResponse:
    alert = get_alert(db, alert_id)
    if alert is None:
        raise not_found("ALERT_NOT_FOUND", "The requested alert does not exist.")
    return escalate_alert(db, alert, payload.reason)


@router.get("/incidents", response_model=IncidentListResponse)
def get_incidents(db: Session = Depends(get_db)) -> IncidentListResponse:
    return IncidentListResponse(incidents=list_incidents(db))


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
def get_incident_by_id(incident_id: UUID, db: Session = Depends(get_db)) -> IncidentResponse:
    incident = get_incident(db, incident_id)
    if incident is None:
        raise not_found("INCIDENT_NOT_FOUND", "The requested incident does not exist.")
    return incident


@router.get("/incidents/{incident_id}/timeline", response_model=IncidentTimelineResponse)
def get_timeline(incident_id: UUID, db: Session = Depends(get_db)) -> IncidentTimelineResponse:
    if get_incident(db, incident_id) is None:
        raise not_found("INCIDENT_NOT_FOUND", "The requested incident does not exist.")
    return IncidentTimelineResponse(
        incident_id=incident_id,
        events=list_incident_events(db, incident_id),
    )


@router.get("/field-reports", response_model=FieldReportListResponse)
def get_field_reports(db: Session = Depends(get_db)) -> FieldReportListResponse:
    return FieldReportListResponse(reports=list_field_reports(db))


@router.post(
    "/field-reports",
    response_model=FieldReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_field_report(payload: FieldReportCreate, db: Session = Depends(get_db)) -> FieldReportResponse:
    return create_field_report(db, payload)
