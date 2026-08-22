"""
Asset Layer Catalog and Sensitivity Weights
Maintains static/semi-static coastal, ecological, and socio-economic asset geometries.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List
from shapely.geometry import Point, Polygon, mapping


# Standard sensitivity weights [1.0 - 5.0]
ASSET_SENSITIVITY_WEIGHTS: Dict[str, float] = {
    "protected_area": 4.8,     # Critical IUCN Category I/II marine reserve / coral ecosystem
    "wetland": 4.2,            # Sensitive mangrove / salt marsh
    "fishery": 3.8,            # High-yield aquaculture / artisanal fishing zone
    "beach": 3.2,              # Public recreation & coastal tourism
    "coastal_population": 3.0, # Populated shoreline settlement
    "port": 2.2                # Industrial shipping terminal / harbor
}


def create_asset_catalog_for_region(region_name: str = "chennai_ennore") -> List[Dict[str, Any]]:
    """
    Generates georeferenced DEMO asset layers for pipeline testing.
    Default region: Ennore Port / Bay of Bengal coastal sector (2017 spill case study geometry).
    These are reference polygons — not live WDPA/GFW downloads.
    """
    now = datetime.now(timezone.utc)
    
    # Ennore / Chennai Coastal Sector (80.20 - 80.40 E, 13.00 - 13.40 N)
    assets = [
        {
            "name": "Pulicat Lake Bird Sanctuary & Mangrove Reserve",
            "asset_type": "protected_area",
            "sensitivity_weight": 4.8,
            "data_source": "WDPA / Ramsar Wetlands (Site #1210)",
            "data_vintage": now,
            "centroid_lon": 80.320,
            "centroid_lat": 13.420,
            "geom_geojson": mapping(
                Polygon([
                    (80.280, 13.380),
                    (80.360, 13.380),
                    (80.350, 13.460),
                    (80.270, 13.460),
                    (80.280, 13.380)
                ])
            ),
            "properties": {
                "iucn_category": "IV",
                "ecosystem": "Mangrove / Coastal Lagoon",
                "protection_status": "Strict Reserve"
            }
        },
        {
            "name": "Kattupalli Coastal Marine Fishery & Crab Grounds",
            "asset_type": "fishery",
            "sensitivity_weight": 3.8,
            "data_source": "Global Fishing Watch AIS / State Fisheries Dept",
            "data_vintage": now,
            "centroid_lon": 80.360,
            "centroid_lat": 13.310,
            "geom_geojson": mapping(
                Polygon([
                    (80.330, 13.270),
                    (80.390, 13.270),
                    (80.380, 13.350),
                    (80.320, 13.350),
                    (80.330, 13.270)
                ])
            ),
            "properties": {
                "active_vessels_daily": 140,
                "annual_catch_tons": 8500,
                "primary_species": "Penaeus monodon / Blue Crab"
            }
        },
        {
            "name": "Kamarajar Port (Ennore Deep-Water Terminal)",
            "asset_type": "port",
            "sensitivity_weight": 2.2,
            "data_source": "National Ports Database / OpenStreetMap",
            "data_vintage": now,
            "centroid_lon": 80.340,
            "centroid_lat": 13.260,
            "geom_geojson": mapping(
                Polygon([
                    (80.325, 13.245),
                    (80.355, 13.245),
                    (80.355, 13.275),
                    (80.325, 13.275),
                    (80.325, 13.245)
                ])
            ),
            "properties": {
                "berths": 9,
                "cargo_type": "Crude Oil / Coal / Containers",
                "traffic_density": "High"
            }
        },
        {
            "name": "Marina Beach Coastal Tourism & Turtle Nesting Zone",
            "asset_type": "beach",
            "sensitivity_weight": 3.5,
            "data_source": "State Coastal Management Authority",
            "data_vintage": now,
            "centroid_lon": 80.285,
            "centroid_lat": 13.050,
            "geom_geojson": mapping(
                Polygon([
                    (80.275, 13.020),
                    (80.295, 13.020),
                    (80.295, 13.080),
                    (80.275, 13.080),
                    (80.275, 13.020)
                ])
            ),
            "properties": {
                "daily_visitors": 45000,
                "olive_ridley_nesting": True,
                "shoreline_km": 6.2
            }
        },
        {
            "name": "Royapuram Coastal Community Settlement",
            "asset_type": "coastal_population",
            "sensitivity_weight": 3.0,
            "data_source": "Global Human Settlement Layer (GHSL)",
            "data_vintage": now,
            "centroid_lon": 80.300,
            "centroid_lat": 13.120,
            "geom_geojson": mapping(
                Polygon([
                    (80.285, 13.100),
                    (80.315, 13.100),
                    (80.315, 13.140),
                    (80.285, 13.140),
                    (80.285, 13.100)
                ])
            ),
            "properties": {
                "population_density_sqkm": 28000,
                "waterfront_dwellings": 1200
            }
        }
    ]

    return assets
