from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


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


class RiskZone(BaseModel):
    location_id: str
    score: int = Field(ge=0, le=100)
    level: str
    lat: float
    lon: float
    data_provenance: str


class RiskZoneResponse(BaseModel):
    zones: list[RiskZone]
