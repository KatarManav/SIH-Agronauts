from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ImpactAssetType(str, Enum):
    ROAD = "ROAD"
    VILLAGE = "VILLAGE"
    BRIDGE = "BRIDGE"
    CRITICAL_ASSET = "CRITICAL_ASSET"


class ExposedAsset(BaseModel):
    id: UUID
    name: str
    asset_type: ImpactAssetType
    distance_km: float = Field(ge=0)
    importance: int = Field(ge=1)
    is_demo: bool


class ImpactResponse(BaseModel):
    location_id: str
    radius_km: float
    potentially_exposed: list[ExposedAsset]
    counts: dict[str, int]
    data_provenance: str


class PriorityItem(BaseModel):
    location_id: str
    score: int = Field(ge=0, le=100)
    priority: str
    exposed_asset_count: int
    data_provenance: str


class PriorityResponse(BaseModel):
    items: list[PriorityItem]


class SatelliteEvidence(BaseModel):
    id: UUID
    platform: str
    product_type: str
    detection_type: str
    confidence: float | None = Field(default=None, ge=0, le=100)
    detected_at: str
    latitude: float
    longitude: float
    change_detected: bool
    data_status: str
    is_simulated: bool


class RiskZone(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    location_id: str
    score: int = Field(ge=0, le=100)
    level: str
    lat: float
    lon: float
    h3_cell: str = Field(alias="h3Cell")
    h3_boundary: list[list[float]] = Field(alias="h3Boundary")
    trend: str
    priority: str
    impact_counts: dict[str, int]
    factors: list[dict[str, str | float | None]]
    satellite_evidence: list[SatelliteEvidence] = Field(
        default_factory=list, alias="satelliteEvidence"
    )
    data_provenance: str


class RiskZoneResponse(BaseModel):
    zones: list[RiskZone]
