from pydantic import BaseModel, Field


class FeatureVector(BaseModel):
    location_id: str
    rainfall_mm: float | None = Field(default=None, ge=0)
    soil_moisture_ratio: float | None = Field(default=None, ge=0, le=1)
    slope_degrees: float | None = Field(default=None, ge=0, le=90)
    susceptibility_index: float | None = Field(default=None, ge=0, le=1)
    source_observation_ids: list[str] = Field(default_factory=list)
