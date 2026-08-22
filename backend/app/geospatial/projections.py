"""
Geospatial Projections and Coordinate Transformations
Preserves CRS metadata and maps between raster pixel space and WGS84 (EPSG:4326).
"""
from typing import List, Tuple
import pyproj
from pyproj import CRS, Transformer


WGS84_CRS = CRS.from_epsg(4326)


class AffineGeoTransform:
    """
    Affine transformation between raster pixel coordinates (row, col)
    and geographic coordinates (lon, lat) in EPSG:4326.
    
    Formula:
        lon = origin_lon + col * pixel_width_deg + row * x_rotation
        lat = origin_lat + col * y_rotation + row * pixel_height_deg (usually negative)
    """
    def __init__(
        self,
        origin_lon: float,
        origin_lat: float,
        pixel_width_deg: float,
        pixel_height_deg: float,
        x_rotation: float = 0.0,
        y_rotation: float = 0.0
    ):
        self.origin_lon = origin_lon
        self.origin_lat = origin_lat
        self.pixel_width_deg = pixel_width_deg
        self.pixel_height_deg = pixel_height_deg
        self.x_rotation = x_rotation
        self.y_rotation = y_rotation

    @classmethod
    def from_bbox_and_shape(
        cls,
        bbox: List[float],  # [min_lon, min_lat, max_lon, max_lat]
        height: int,
        width: int
    ) -> "AffineGeoTransform":
        """Constructs transform from bounding box and raster pixel dimensions."""
        min_lon, min_lat, max_lon, max_lat = bbox
        pixel_w = (max_lon - min_lon) / max(width, 1)
        pixel_h = -(max_lat - min_lat) / max(height, 1)  # top-down row ordering
        return cls(
            origin_lon=min_lon,
            origin_lat=max_lat,
            pixel_width_deg=pixel_w,
            pixel_height_deg=pixel_h
        )

    def pixel_to_geo(self, row: float, col: float) -> Tuple[float, float]:
        """Converts (row, col) in pixel space to (longitude, latitude) in EPSG:4326."""
        lon = self.origin_lon + col * self.pixel_width_deg + row * self.x_rotation
        lat = self.origin_lat + col * self.y_rotation + row * self.pixel_height_deg
        return round(lon, 7), round(lat, 7)

    def geo_to_pixel(self, lon: float, lat: float) -> Tuple[float, float]:
        """Converts (lon, lat) to (row, col) in pixel coordinates."""
        col = (lon - self.origin_lon) / self.pixel_width_deg
        row = (lat - self.origin_lat) / self.pixel_height_deg
        return row, col


def get_utm_crs_for_lon_lat(lon: float, lat: float) -> CRS:
    """Returns appropriate projected UTM CRS for accurate planar distance calculations."""
    utm_zone = int((lon + 180) / 6) + 1
    is_northern = lat >= 0
    epsg_code = 32600 + utm_zone if is_northern else 32700 + utm_zone
    return CRS.from_epsg(epsg_code)
