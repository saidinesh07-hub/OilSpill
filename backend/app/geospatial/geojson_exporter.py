"""
GeoJSON Serialization Utilities
Converts database entities and polygons to standard RFC 7946 GeoJSON FeatureCollections.
"""
from typing import Any, Dict, List, Optional
from shapely.geometry import mapping


def to_geojson_feature(
    geometry: Any,  # Shapely geom or GeoJSON dict
    properties: Dict[str, Any],
    feature_id: Optional[str] = None
) -> Dict[str, Any]:
    """Wraps geometry and properties into a standard GeoJSON Feature."""
    geom_dict = mapping(geometry) if hasattr(geometry, "__geo_interface__") else geometry
    feature = {
        "type": "Feature",
        "geometry": geom_dict,
        "properties": properties
    }
    if feature_id:
        feature["id"] = feature_id
    return feature


def to_geojson_feature_collection(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Wraps list of GeoJSON Features into a FeatureCollection."""
    return {
        "type": "FeatureCollection",
        "features": features
    }
