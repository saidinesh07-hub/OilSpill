"""
Geospatial Geometry Operations Module
Implements exact geodetic area on the WGS84 ellipsoid, valid polygon repair, and distance metrics.
"""
from typing import Any, Dict, List, Tuple
import numpy as np
import pyproj
from pyproj import Geod
from shapely.geometry import Polygon, MultiPolygon, shape, mapping
from shapely.validation import make_valid
from shapely.ops import unary_union


GEOD_WGS84 = Geod(ellps="WGS84")


def compute_geodetic_area_km2(polygon_geom: Polygon) -> float:
    """
    Calculates exact physical surface area on the WGS84 ellipsoid in square kilometers.
    NEVER calculates area by multiplying degrees squared!
    """
    if polygon_geom is None or polygon_geom.is_empty:
        return 0.0

    if isinstance(polygon_geom, MultiPolygon):
        total_area_m2 = 0.0
        for poly in polygon_geom.geoms:
            lons, lats = poly.exterior.coords.xy
            poly_area, _ = GEOD_WGS84.polygon_area_perimeter(lons, lats)
            total_area_m2 += abs(poly_area)
            # Subtract interior rings (holes)
            for interior in poly.interiors:
                hlons, hlats = interior.coords.xy
                h_area, _ = GEOD_WGS84.polygon_area_perimeter(hlons, hlats)
                total_area_m2 -= abs(h_area)
        return round(abs(total_area_m2) / 1e6, 4)

    lons, lats = polygon_geom.exterior.coords.xy
    area_m2, _ = GEOD_WGS84.polygon_area_perimeter(lons, lats)
    total_area_m2 = abs(area_m2)

    for interior in polygon_geom.interiors:
        hlons, hlats = interior.coords.xy
        h_area, _ = GEOD_WGS84.polygon_area_perimeter(hlons, hlats)
        total_area_m2 -= abs(h_area)

    return round(abs(total_area_m2) / 1e6, 4)


def compute_geodetic_perimeter_km(polygon_geom: Polygon) -> float:
    """Calculates geodetic perimeter on WGS84 in kilometers."""
    if polygon_geom is None or polygon_geom.is_empty:
        return 0.0
    
    if isinstance(polygon_geom, MultiPolygon):
        total_perim_m = 0.0
        for poly in polygon_geom.geoms:
            lons, lats = poly.exterior.coords.xy
            _, perim = GEOD_WGS84.polygon_area_perimeter(lons, lats)
            total_perim_m += perim
        return round(total_perim_m / 1000.0, 3)

    lons, lats = polygon_geom.exterior.coords.xy
    _, perim_m = GEOD_WGS84.polygon_area_perimeter(lons, lats)
    return round(perim_m / 1000.0, 3)


def get_geodesic_distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculates great-circle distance between two WGS84 points in kilometers."""
    _, _, dist_m = GEOD_WGS84.inv(lon1, lat1, lon2, lat2)
    return round(dist_m / 1000.0, 3)


def get_geodesic_forward_point(lon: float, lat: float, azimuth_deg: float, distance_km: float) -> Tuple[float, float]:
    """Calculates end coordinates given start point, forward bearing, and distance in km."""
    end_lon, end_lat, _ = GEOD_WGS84.fwd(lon, lat, azimuth_deg, distance_km * 1000.0)
    return round(end_lon, 7), round(end_lat, 7)


def get_bearing_degrees(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculates forward initial azimuth (heading) in degrees [0..360]."""
    fwd_az, _, _ = GEOD_WGS84.inv(lon1, lat1, lon2, lat2)
    return round((fwd_az + 360.0) % 360.0, 2)


def repair_and_clean_geometry(geom: Polygon, simplify_tolerance_deg: float = 0.0001) -> Polygon:
    """
    Repairs self-intersecting or invalid polygons and applies subtle Douglas-Peucker simplification.
    """
    if not geom.is_valid:
        geom = make_valid(geom)

    if isinstance(geom, MultiPolygon):
        valid_polys = [p for p in geom.geoms if isinstance(p, Polygon) and p.is_valid and not p.is_empty]
        if not valid_polys:
            return Polygon()
        geom = unary_union(valid_polys)

    if simplify_tolerance_deg > 0:
        geom = geom.simplify(simplify_tolerance_deg, preserve_topology=True)

    return geom
