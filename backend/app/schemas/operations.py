from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Priority


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: str
    severity: str
    hazard: str
    reason: str
    action: str
    status: str
    created_at: datetime


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(min_length=1, max_length=200)


class AssignmentRequest(BaseModel):
    assigned_to: str = Field(min_length=1, max_length=200)


class EscalationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: str
    status: str
    priority: Priority
    summary: str
    created_at: datetime


class IncidentListResponse(BaseModel):
    incidents: list[IncidentResponse]


class IncidentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    status: str
    note: str
    created_at: datetime


class IncidentTimelineResponse(BaseModel):
    incident_id: UUID
    events: list[IncidentEventResponse]


class FieldReportCreate(BaseModel):
    location_id: str = Field(min_length=1, max_length=64)
    observation: str = Field(min_length=1, max_length=5000)
    reporter_type: str = Field(min_length=1, max_length=64)
    photo_path: str | None = Field(default=None, max_length=500)


class FieldReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: str
    observation: str
    reporter_type: str
    photo_path: str | None
    reported_at: datetime


class FieldReportListResponse(BaseModel):
    reports: list[FieldReportResponse]
