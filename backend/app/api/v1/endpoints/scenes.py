"""
Satellite Scenes and Observation Endpoints
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.database.models import SatelliteScene, Observation
from backend.app.schemas.scenes import SatelliteSceneResponse, SatelliteSceneCreate, ObservationResponse
from backend.app.schemas.common import APIResponse
from backend.app.services.scene_ingestion import SceneIngestionService

router = APIRouter(prefix="/scenes", tags=["Satellite Scenes"])


@router.get("", response_model=APIResponse[List[SatelliteSceneResponse]])
def list_scenes(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    scenes = db.query(SatelliteScene).order_by(SatelliteScene.acquisition_time.desc()).offset(skip).limit(limit).all()
    return APIResponse(data=scenes)


@router.get("/search/cdse")
def search_cdse_scenes(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: Session = Depends(get_db),
):
    """Search Copernicus Data Space for Sentinel-1 products (requires CDSE credentials)."""
    ingestion = SceneIngestionService(db=db)
    result = ingestion.search_cdse_sentinel1(
        bbox=[min_lon, min_lat, max_lon, max_lat],
        start=start,
        end=end,
    )
    return APIResponse(data=result)


@router.get("/{scene_id}", response_model=APIResponse[SatelliteSceneResponse])
def get_scene(scene_id: str, db: Session = Depends(get_db)):
    scene = db.query(SatelliteScene).filter(SatelliteScene.scene_id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return APIResponse(data=scene)


@router.get("/{scene_id}/observations", response_model=APIResponse[List[ObservationResponse]])
def get_scene_observations(scene_id: str, db: Session = Depends(get_db)):
    obs = db.query(Observation).filter(Observation.scene_id == scene_id).all()
    return APIResponse(data=obs)
