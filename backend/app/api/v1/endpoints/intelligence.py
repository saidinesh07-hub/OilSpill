from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.services.intelligence_orchestrator import IntelligenceOrchestrator

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

@router.get("/spill/{spill_id}")
def get_spill_intelligence(spill_id: str, db: Session = Depends(get_db)):
    orchestrator = IntelligenceOrchestrator(db)
    return orchestrator.get_unified_intelligence(spill_id)
