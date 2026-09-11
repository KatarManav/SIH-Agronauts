from app.db.base import Base
from app.db.session import engine
from sqlalchemy import text
from app.models import (  # noqa: F401
    Alert,
    EnvironmentalObservation,
    FieldReport,
    InfrastructureAsset,
    Incident,
    IncidentEvent,
    Location,
    ResponseAction,
    RiskAssessment,
    RiskFactor,
    SatelliteObservation,
)


def create_tables() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        Base.metadata.create_all(bind=connection)
