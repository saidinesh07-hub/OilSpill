"""
Tracked Slicks and Temporal Evolution Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.database.models import TrackedSlick, TemporalObservation
from backend.app.schemas.temporal import TrackedSlickResponse, TemporalObservationResponse
from backend.app.schemas.common import APIResponse

router = APIRouter(prefix="/tracks", tags=["Temporal Tracking"])


@router.get("", response_model=APIResponse[List[TrackedSlickResponse]])
def list_tracks(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(TrackedSlick)
    if status:
        query = query.filter(TrackedSlick.current_status == status.upper())
    tracks = query.order_by(TrackedSlick.last_seen.desc()).all()
    return APIResponse(data=tracks)


@router.get("/{track_id}", response_model=APIResponse[TrackedSlickResponse])
def get_track(track_id: str, db: Session = Depends(get_db)):
    track = db.query(TrackedSlick).filter(TrackedSlick.track_id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Tracked slick not found")
    return APIResponse(data=track)


@router.get("/{track_id}/history", response_model=APIResponse[List[TemporalObservationResponse]])
def get_track_history(track_id: str, db: Session = Depends(get_db)):
    track = db.query(TrackedSlick).filter(TrackedSlick.track_id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    history = db.query(TemporalObservation).filter(TemporalObservation.track_id == track_id).order_by(TemporalObservation.observation_time.asc()).all()
    return APIResponse(data=history)
