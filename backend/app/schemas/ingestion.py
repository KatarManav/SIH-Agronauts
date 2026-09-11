from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EnvironmentalObservationCreate(BaseModel):
    location_id: str = Field(min_length=1, max_length=64)
    source: str = Field(min_length=1, max_length=100)
    data_class: str = Field(min_length=1, max_length=64)
    observed_at: datetime
    values: dict[str, float | str | None] = Field(min_length=1)
    is_demo: bool = False


class EnvironmentalObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    location_id: str
    source: str
    data_class: str
    observed_at: datetime
    values: dict[str, float | str | None]
    is_demo: bool
    created_at: datetime


class EnvironmentalObservationListResponse(BaseModel):
    observations: list[EnvironmentalObservationResponse]
