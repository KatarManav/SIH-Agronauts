from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AlertStatus,
    Incident,
    IncidentEvent,
    IncidentStatus,
    Priority,
    RiskAssessment,
    RiskFactor,
    RiskLevel,
    RiskTrend,
)
from app.services.features import build_feature_vector


@dataclass(frozen=True)
class RiskResult:
    score: int
    level: RiskLevel
    trend: RiskTrend
    priority: Priority
    factors: list[RiskFactor]


def _level(score: int) -> RiskLevel:
    if score >= 75:
        return RiskLevel.CRITICAL
    if score >= 50:
        return RiskLevel.HIGH
    if score >= 25:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def _priority(score: int) -> Priority:
    if score >= 75:
        return Priority.P1
    if score >= 50:
        return Priority.P2
    if score >= 25:
        return Priority.P3
    return Priority.P4


def _scaled(value: float | None, maximum: float) -> float:
    if value is None:
        return 0
    return max(0, min(100, value / maximum * 100))


def calculate_risk(db: Session, location_id: str) -> RiskResult | None:
    features = build_feature_vector(db, location_id)
    components = [
        ("Rainfall", features.rainfall_mm, "mm", _scaled(features.rainfall_mm, 200), 0.4),
        (
            "Soil Moisture",
            features.soil_moisture_ratio,
            "ratio",
            _scaled(features.soil_moisture_ratio, 1),
            0.3,
        ),
        (
            "Slope",
            features.slope_degrees,
            "degrees",
            _scaled(features.slope_degrees, 45),
            0.2,
        ),
        (
            "Susceptibility",
            features.susceptibility_index,
            "index",
            _scaled(features.susceptibility_index, 1),
            0.1,
        ),
    ]
    if not any(value is not None for _, value, _, _, _ in components):
        return None

    score = round(sum(normalized * weight for _, _, _, normalized, weight in components))
    previous = db.scalar(
        select(RiskAssessment)
        .where(RiskAssessment.location_id == location_id)
        .order_by(RiskAssessment.assessed_at.desc())
    )
    trend = RiskTrend.STABLE
    if previous is not None:
        trend = (
            RiskTrend.RISING if score > previous.score
            else RiskTrend.FALLING if score < previous.score
            else RiskTrend.STABLE
        )
    factors = [
        RiskFactor(
            name=name,
            value=value,
            unit=unit,
            contribution="HIGH" if normalized >= 67 else "MEDIUM" if normalized >= 34 else "LOW",
            direction="INCREASES_RISK" if normalized > 0 else "NO_SIGNAL",
        )
        for name, value, unit, normalized, _ in components
        if value is not None
    ]
    return RiskResult(score, _level(score), trend, _priority(score), factors)


def persist_risk(db: Session, location_id: str, result: RiskResult) -> RiskAssessment:
    assessment = RiskAssessment(
        location_id=location_id,
        score=result.score,
        level=result.level,
        trend=result.trend,
    )
    assessment.factors = result.factors
    db.add(assessment)
    if result.score >= 75:
        db.flush()
        existing = db.scalar(
            select(Alert).where(
                Alert.location_id == location_id,
                Alert.status == AlertStatus.ACTIVE,
                Alert.reason == "RISK_ENGINE_THRESHOLD",
            )
        )
        if existing is None:
            db.add(Alert(
                location_id=location_id,
                severity=result.level.value,
                hazard="LANDSLIDE",
                reason="RISK_ENGINE_THRESHOLD",
                action="AVOID_HILLSIDE_ROAD",
            ))
    db.commit()
    db.refresh(assessment)
    return assessment
