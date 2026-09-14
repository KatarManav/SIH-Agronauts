from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import RiskLevel, RiskTrend


class RiskTrendPoint(BaseModel):
    assessed_at: datetime
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    trend: RiskTrend


class RiskTrendResponse(BaseModel):
    location_id: str
    points: list[RiskTrendPoint]
    data_provenance: str
