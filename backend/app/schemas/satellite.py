from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SatelliteObservationCreate(BaseModel):
    location_id: str = Field(min_length=1, max_length=64)
    platform: str = Field(min_length=1, max_length=64)
    product_type: str = Field(min_length=1, max_length=100)
    acquisition_at: datetime
    processing_quality: float | None = Field(default=None, ge=0, le=1)
    change_detected: bool = False
    evidence: dict[str, float | str | bool | None] = Field(default_factory=dict)
    is_demo: bool = False


class SatelliteObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: str
    platform: str
    product_type: str
    acquisition_at: datetime
    processed_at: datetime
    processing_quality: float | None
    change_detected: bool
    evidence: dict[str, float | str | bool | None]
    is_demo: bool
    freshness_hours: float = Field(ge=0)
    latitude: float
    longitude: float
    detection_type: str
    confidence: float | None = Field(default=None, ge=0, le=100)
    detected_at: datetime
    data_status: str
    is_simulated: bool


class SatelliteObservationListResponse(BaseModel):
    observations: list[SatelliteObservationResponse]


class SatelliteDetectionListResponse(BaseModel):
    location: dict[str, str]
    detections: list[SatelliteObservationResponse]
    data_status: str
    is_simulated: bool
