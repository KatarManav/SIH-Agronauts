from pydantic import BaseModel, Field

from app.schemas.impact import SatelliteEvidence


class H3RiskFactor(BaseModel):
    name: str
    impact: str
    value: float | None = None
    unit: str | None = None


class H3RiskCell(BaseModel):
    h3_cell: str = Field(alias="h3Cell")
    boundary: list[list[float]]
    risk_score: int = Field(alias="riskScore", ge=0, le=100)
    risk_level: str = Field(alias="riskLevel")
    trend: str
    factors: list[H3RiskFactor]
    priority: str
    impact_counts: dict[str, int] = Field(alias="impactCounts")
    data_status: str = Field(default="DEMO", alias="dataStatus")
    satellite_evidence: list[SatelliteEvidence] = Field(
        default_factory=list, alias="satelliteEvidence"
    )

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class RiskGridLocation(BaseModel):
    id: str
    name: str
    center: dict[str, float]


class RiskGridResponse(BaseModel):
    location: RiskGridLocation | None
    cells: list[H3RiskCell]
