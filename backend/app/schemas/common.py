from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class APIErrorDetail(BaseModel):
    code: str
    message: str


class APIErrorResponse(BaseModel):
    error: APIErrorDetail


class RiskLevel(str, Enum):
    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskTrend(str, Enum):
    UNKNOWN = "UNKNOWN"
    STABLE = "STABLE"
    RISING = "RISING"
    FALLING = "FALLING"


class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    lat: float = Field(validation_alias="latitude", serialization_alias="lat")
    lon: float = Field(validation_alias="longitude", serialization_alias="lon")
