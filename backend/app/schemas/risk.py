from pydantic import BaseModel, Field

from app.schemas.common import LocationResponse, Priority, RiskLevel, RiskTrend


class RiskFactorResponse(BaseModel):
    name: str
    value: float | None = None
    unit: str | None = None
    contribution: str
    direction: str


class ImpactSummary(BaseModel):
    roads: int = 0
    villages: int = 0
    bridges: int = 0
    critical_assets: int = 0


class RiskSummary(BaseModel):
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    trend: RiskTrend


class RiskResponse(BaseModel):
    location: LocationResponse
    risk: RiskSummary
    factors: list[RiskFactorResponse] = Field(default_factory=list)
    impact: ImpactSummary = Field(default_factory=ImpactSummary)
    priority: Priority
