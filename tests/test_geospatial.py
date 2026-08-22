"""
Unit Tests for Geospatial Pipeline and WGS84 Geodesic Calculations
"""
import pytest
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point
from backend.app.geospatial.projections import AffineGeoTransform, get_utm_crs_for_lon_lat
from backend.app.geospatial.geometry_ops import (
    compute_geodetic_area_km2,
    compute_geodetic_perimeter_km,
    get_geodesic_distance_km,
    get_bearing_degrees,
    repair_and_clean_geometry
)


def test_affine_transform_roundtrip():
    bbox = [80.0, 13.0, 81.0, 14.0]
    transform = AffineGeoTransform.from_bbox_and_shape(bbox, height=1000, width=1000)

    # Center pixel
    r, c = 500, 500
    lon, lat = transform.pixel_to_geo(r, c)
    assert abs(lon - 80.5) < 1e-4
    assert abs(lat - 13.5) < 1e-4

    # Back to pixel
    r_rev, c_rev = transform.geo_to_pixel(lon, lat)
    assert abs(r - r_rev) < 1e-3
    assert abs(c - c_rev) < 1e-3


def test_geodetic_area_wgs84_accuracy():
    # 0.1 degree square near equator (~11.13 km x 11.13 km ≈ 123.8 km²)
    poly = Polygon([(0.0, 0.0), (0.1, 0.0), (0.1, 0.1), (0.0, 0.1), (0.0, 0.0)])
    area_km2 = compute_geodetic_area_km2(poly)
    
    # Area should be ~123.6 - 123.9 km2, definitely not degrees squared (0.01)!
    assert 120.0 < area_km2 < 126.0
    assert area_km2 != 0.01  # Crucial check: not lat/lon degree squared


def test_geodesic_distance():
    # Chennai to Ennore Port (~20 km north)
    dist_km = get_geodesic_distance_km(80.27, 13.08, 80.34, 13.26)
    assert 18.0 < dist_km < 25.0


def test_bearing_calculation():
    # Pure North
    bearing_n = get_bearing_degrees(80.0, 13.0, 80.0, 14.0)
    assert abs(bearing_n - 0.0) < 1.0 or abs(bearing_n - 360.0) < 1.0

    # Pure East
    bearing_e = get_bearing_degrees(80.0, 13.0, 81.0, 13.0)
    assert abs(bearing_e - 90.0) < 2.0


def test_geometry_repair():
    # Self-intersecting bowtie polygon
    bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
    assert not bowtie.is_valid

    repaired = repair_and_clean_geometry(bowtie)
    assert repaired.is_valid
