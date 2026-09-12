from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    health, scenes, detections, tracks, forecasts, environmental, assets, impact_risk, assistant, pipeline, analysis, incidents, satellite, maritime, intelligence
)
api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(scenes.router)
api_router.include_router(detections.router)
api_router.include_router(tracks.router)
api_router.include_router(forecasts.router)
api_router.include_router(environmental.router)
api_router.include_router(assets.router)
api_router.include_router(impact_risk.router)
api_router.include_router(assistant.router)
api_router.include_router(pipeline.router)
api_router.include_router(analysis.router)
api_router.include_router(incidents.router)
api_router.include_router(satellite.router)
api_router.include_router(maritime.router)
api_router.include_router(intelligence.router)
