from pydantic import BaseModel

from app.schemas.risk import RiskResponse


class RiskCalculationResponse(BaseModel):
    model_risk_type: str
    risk: RiskResponse
