from fastapi import APIRouter

from app.api.routes import engine, health, impact, ingestion, locations, operations, risk, satellite

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(locations.router)
api_router.include_router(risk.router)
api_router.include_router(operations.router)
api_router.include_router(ingestion.router)
api_router.include_router(engine.router)
api_router.include_router(impact.router)
api_router.include_router(satellite.router)
