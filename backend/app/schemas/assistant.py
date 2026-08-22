"""
AI Assistant Query and Grounded Response Schemas
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AssistantQueryRequest(BaseModel):
    question: str
    track_id: Optional[str] = None
    observation_id: Optional[str] = None
    session_id: Optional[str] = None


class GroundedCitation(BaseModel):
    entity_type: str  # "detection", "track", "forecast", "impact", "risk", "environmental", "asset"
    entity_id: str
    label: str
    source_table: str
    data_timestamp: str
    value_snippet: str
    coordinates: Optional[List[float]] = None  # [lon, lat] for interactive map jumping


class AssistantQueryResponse(BaseModel):
    answer: str
    intent_detected: str
    is_grounded: bool = True
    grounding_confidence: float = 1.0
    citations: List[GroundedCitation] = []
    retrieved_data_summary: Dict[str, Any] = {}
    suggested_followups: List[str] = []
