"""
Trajectory Forecast Endpoints
Serves multi-horizon forecast bands (6h, 12h, 24h, 48h) and GeoJSON uncertainty polygons.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.database.models import ForecastRun, ForecastBand, TrackedSlick
from backend.app.schemas.forecasting import ForecastRunResponse, ForecastBandResponse
from backend.app.schemas.common import APIResponse, GeoJSONFeatureCollection
from backend.app.geospatial.geojson_exporter import to_geojson_feature, to_geojson_feature_collection

router = APIRouter(prefix="/forecasts", tags=["Trajectory Forecasting"])


@router.get("/latest", response_model=APIResponse[Optional[ForecastRunResponse]])
def get_latest_forecast(track_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ForecastRun)
    if track_id:
        query = query.filter(ForecastRun.track_id == track_id)
    forecast = query.order_by(ForecastRun.run_time.desc()).first()
    return APIResponse(data=forecast)


@router.get("/{forecast_run_id}", response_model=APIResponse[ForecastRunResponse])
def get_forecast(forecast_run_id: str, db: Session = Depends(get_db)):
    forecast = db.query(ForecastRun).filter(ForecastRun.forecast_run_id == forecast_run_id).first()
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    return APIResponse(data=forecast)


@router.get("/{forecast_run_id}/geojson", response_model=GeoJSONFeatureCollection)
def get_forecast_geojson(
    forecast_run_id: str,
    horizon_hours: Optional[int] = None,
    confidence_level: Optional[float] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ForecastBand).filter(ForecastBand.forecast_run_id == forecast_run_id)
    if horizon_hours is not None:
        query = query.filter(ForecastBand.horizon_hours == horizon_hours)
    if confidence_level is not None:
        query = query.filter(ForecastBand.confidence_level == confidence_level)

    bands = query.order_by(ForecastBand.horizon_hours.asc(), ForecastBand.confidence_level.desc()).all()

    features = []
    for b in bands:
        feat = to_geojson_feature(
            geometry=b.geom_geojson,
            properties={
                "band_id": b.id,
                "forecast_run_id": b.forecast_run_id,
                "horizon_hours": b.horizon_hours,
                "confidence_level": b.confidence_level,
                "target_time": b.target_time.isoformat(),
                "area_km2": b.area_km2,
                "centroid_lat": b.centroid_lat,
                "centroid_lon": b.centroid_lon,
                "mean_speed_kmh": b.mean_speed_kmh
            },
            feature_id=b.id
        )
        features.append(feat)

    return to_geojson_feature_collection(features)
