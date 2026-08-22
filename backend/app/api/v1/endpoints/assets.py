"""
Asset Layer Endpoints
Serves static/semi-static coastal asset layers and GeoJSON geometries.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.database.models import Asset
from backend.app.schemas.assets import AssetResponse
from backend.app.schemas.common import APIResponse, GeoJSONFeatureCollection
from backend.app.geospatial.geojson_exporter import to_geojson_feature, to_geojson_feature_collection

router = APIRouter(prefix="/assets", tags=["Asset Layers"])


@router.get("", response_model=APIResponse[List[AssetResponse]])
def list_assets(
    asset_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Asset)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type.lower())
    assets = query.all()
    return APIResponse(data=assets)


@router.get("/geojson", response_model=GeoJSONFeatureCollection)
def get_assets_geojson(
    asset_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Asset)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type.lower())
    assets = query.all()

    features = []
    for a in assets:
        feat = to_geojson_feature(
            geometry=a.geom_geojson,
            properties={
                "asset_id": a.asset_id,
                "name": a.name,
                "asset_type": a.asset_type,
                "sensitivity_weight": a.sensitivity_weight,
                "data_source": a.data_source,
                "data_vintage": a.data_vintage.isoformat(),
                "properties": a.properties
            },
            feature_id=a.asset_id
        )
        features.append(feat)

    return to_geojson_feature_collection(features)
