"""
Spill Detections Endpoint
Returns tabular detection details and standard RFC 7946 GeoJSON FeatureCollections.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.database.models import SpillDetection
from backend.app.schemas.detections import SpillDetectionResponse
from backend.app.schemas.common import APIResponse, GeoJSONFeatureCollection
from backend.app.geospatial.geojson_exporter import to_geojson_feature, to_geojson_feature_collection

router = APIRouter(prefix="/detections", tags=["Detections"])


@router.get("", response_model=APIResponse[List[SpillDetectionResponse]])
def list_detections(
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    predicted_class: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(SpillDetection).filter(SpillDetection.confidence >= min_confidence)
    if predicted_class:
        query = query.filter(SpillDetection.predicted_class == predicted_class)
    detections = query.order_by(SpillDetection.created_at.desc()).limit(limit).all()
    return APIResponse(data=detections)


@router.get("/geojson", response_model=GeoJSONFeatureCollection)
def get_detections_geojson(
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    predicted_class: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(SpillDetection).filter(SpillDetection.confidence >= min_confidence)
    if predicted_class:
        query = query.filter(SpillDetection.predicted_class == predicted_class)
    detections = query.all()

    features = []
    for d in detections:
        feat = to_geojson_feature(
            geometry=d.geom_geojson,
            properties={
                "detection_id": d.detection_id,
                "predicted_class": d.predicted_class,
                "area_km2": d.area_km2,
                "perimeter_km": d.perimeter_km,
                "confidence": d.confidence,
                "lookalike_risk_score": d.lookalike_risk_score,
                "morphology": d.morphology_features,
                "model_version": d.model_version
            },
            feature_id=d.detection_id
        )
        features.append(feat)

    return to_geojson_feature_collection(features)
