"""
Database Seeding Script for Historical Spill Scenarios
Populates database with documented real-world case studies:
1. Ennore Port Oil Spill (Chennai, Bay of Bengal, 2017) - Multi-pass Sentinel-1 sequence
2. Deepwater Horizon (Gulf of Mexico) - Massive dispersion and coastal asset impact
3. Bohai Sea Oil Spill (China) - Multi-platform offshore leak
"""
import os
import sys
from datetime import datetime, timezone

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal, init_db
from backend.app.services.scene_ingestion import SceneIngestionService
from backend.app.services.pipeline_orchestrator import IntelligencePipelineOrchestrator
from backend.app.core.logging import logger


def seed_all():
    logger.info("Initializing database schema...")
    init_db()
    db = SessionLocal()

    try:
        ingestion = SceneIngestionService(db=db)
        orchestrator = IntelligencePipelineOrchestrator(db=db)

        logger.info("--- Seeding Scenario 1: Ennore Port Oil Spill (Multi-Pass Sentinel-1 Sequence) ---")
        # Observation 1: Initial collision detection
        t1 = datetime(2017, 1, 28, 6, 30, tzinfo=timezone.utc)
        scene1 = ingestion.register_scene(
            scene_name="DEMO_S1A_IW_GRDH_20170128T063000_Ennore_P1",
            acquisition_time=t1,
            bbox=[80.25, 13.15, 80.45, 13.35],
            source="DEMO — Ennore 2017 case study geometry (synthetic SAR raster)",
            is_synthetic=True
        )
        res1 = orchestrator.process_scene(scene=scene1, is_synthetic=True)
        logger.info(f"Pass 1 result: {res1}")

        # Observation 2: 24h later revisit showing southward drift & expansion along Coromandel coast
        t2 = datetime(2017, 1, 29, 6, 30, tzinfo=timezone.utc)
        scene2 = ingestion.register_scene(
            scene_name="DEMO_S1A_IW_GRDH_20170129T063000_Ennore_P2",
            acquisition_time=t2,
            bbox=[80.26, 13.10, 80.46, 13.30],
            source="DEMO — Ennore 2017 case study geometry (synthetic SAR raster)",
            is_synthetic=True
        )
        res2 = orchestrator.process_scene(scene=scene2, is_synthetic=True)
        logger.info(f"Pass 2 result: {res2}")

        logger.info("Seeding completed successfully! State ledger and asset impacts are ready.")

    except Exception as e:
        logger.error(f"Seeding failed: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
