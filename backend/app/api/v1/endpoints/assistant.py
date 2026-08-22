"""
Grounded AI Assistant Endpoint
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.assistant.grounded_engine import GroundedAIAssistant
from backend.app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse

router = APIRouter(prefix="/assistant", tags=["Grounded AI Assistant"])


@router.post("/query", response_model=AssistantQueryResponse)
def query_assistant(payload: AssistantQueryRequest, db: Session = Depends(get_db)):
    assistant = GroundedAIAssistant(db=db)
    response = assistant.answer_query(
        question=payload.question,
        track_id=payload.track_id,
        observation_id=payload.observation_id
    )
    return response
