"""
Pipeline Processing and Case Study Ingestion Endpoints
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.database.models import SatelliteScene
from backend.app.services.pipeline_orchestrator import IntelligencePipelineOrchestrator
from backend.app.services.scene_ingestion import SceneIngestionService
from backend.app.schemas.common import APIResponse

router = APIRouter(prefix="/pipeline", tags=["Pipeline Execution & Case Studies"])


@router.post("/process/{scene_id}")
def process_scene_pipeline(scene_id: str, db: Session = Depends(get_db)):
    scene = db.query(SatelliteScene).filter(SatelliteScene.scene_id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    orchestrator = IntelligencePipelineOrchestrator(db=db)
    result = orchestrator.process_scene(scene=scene, is_synthetic=scene.is_synthetic)
    return APIResponse(data=result, message="Pipeline executed successfully")


@router.post("/case_studies/seed")
def seed_case_studies(db: Session = Depends(get_db)):
    """
    Seeds the documented multi-pass DEMO case study (Ennore Port 2017 geometry)
    using SYNTHETIC SAR rasters — not real Sentinel-1 observations.
    """
    ingestion = SceneIngestionService(db=db)
    orchestrator = IntelligencePipelineOrchestrator(db=db)

    # Base acquisition time for Ennore spill
    t1 = datetime(2017, 1, 28, 6, 30, tzinfo=timezone.utc)
    t2 = datetime(2017, 1, 29, 6, 30, tzinfo=timezone.utc)

    # Pass 1: Initial Detection
    scene1 = ingestion.register_scene(
        scene_name="DEMO_S1A_IW_GRDH_20170128T063000_Ennore_P1",
        acquisition_time=t1,
        bbox=[80.25, 13.15, 80.45, 13.35],
        source="DEMO — Ennore 2017 case study geometry (synthetic SAR raster)",
        is_synthetic=True
    )
    res1 = orchestrator.process_scene(scene=scene1, is_synthetic=True)

    scene2 = ingestion.register_scene(
        scene_name="DEMO_S1A_IW_GRDH_20170129T063000_Ennore_P2",
        acquisition_time=t2,
        bbox=[80.26, 13.10, 80.46, 13.30],
        source="DEMO — Ennore 2017 case study geometry (synthetic SAR raster)",
        is_synthetic=True
    )
    res2 = orchestrator.process_scene(scene=scene2, is_synthetic=True)

    return APIResponse(
        data={"scene_1": res1, "scene_2": res2, "data_mode": "DEMO_DATA"},
        message="Multi-pass DEMO case study seeded (synthetic SAR). Not real satellite data."
    )
