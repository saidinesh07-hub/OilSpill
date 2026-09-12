from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

from backend.app.database.session import get_db
from backend.app.database.models import Incident
from backend.app.schemas.common import APIResponse
from backend.app.services.cdse_client import CDSEClient
from backend.app.intelligence.geocoding import NominatimGeocodingProvider, aoi_from_point

router = APIRouter(prefix="/location", tags=["Location & Incidents"])


class IncidentCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    mode: str = "DEMO"
    spill_type: Optional[str] = "UNKNOWN"


def _demo_payload(lat: float, lon: float, name: str) -> Dict[str, Any]:
    bbox, aoi = aoi_from_point(lat, lon, 25.0)
    spill_lon = lon + 0.08
    spill_lat = lat + 0.02
    spill_geom = {
        "type": "Polygon",
        "coordinates": [[
            [spill_lon - 0.03, spill_lat - 0.01],
            [spill_lon + 0.04, spill_lat - 0.015],
            [spill_lon + 0.05, spill_lat + 0.02],
            [spill_lon - 0.02, spill_lat + 0.015],
            [spill_lon - 0.03, spill_lat - 0.01],
        ]]
    }
    fb_geom = {
        "type": "Polygon",
        "coordinates": [[
            [spill_lon - 0.03, spill_lat - 0.01],
            [spill_lon + 0.06, spill_lat - 0.02],
            [spill_lon + 0.08, spill_lat + 0.04],
            [spill_lon - 0.01, spill_lat + 0.03],
            [spill_lon - 0.03, spill_lat - 0.01],
        ]]
    }
    
    scene = {
        "scene_id": "DEMO-SYNTHETIC-SCENE",
        "scene_name": f"DEMO_S1A_IW_GRDH around {name}",
        "source": "DEMO synthetic Sentinel-1-like scene",
        "sensor_mode": "IW",
        "polarization": ["VV", "VH"],
        "acquisition_time": datetime.now(timezone.utc).isoformat(),
        "footprint_geojson": aoi,
        "bbox": bbox,
        "is_synthetic": True,
        "ingestion_status": "DEMO",
        "product_id": "DEMO-SYNTHETIC",
        "polarisation": "VV,VH",
        "data_status": "DEMO",
    }
    vessels = [
        {
            "mmsi": "DEMO0001",
            "name": "DEMO TANKER ALPHA",
            "vessel_type": "Tanker (DEMO)",
            "latitude": lat + 0.03,
            "longitude": lon + 0.05,
            "speed": 8.2,
            "heading": 120,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "DEMO / SYNTHETIC DATA",
            "freshness": "DEMO",
        }
    ]
    infrastructure = [
        {
            "name": "DEMO Port Terminal",
            "type": "PORT",
            "latitude": lat - 0.02,
            "longitude": lon - 0.01,
            "source": "DEMO / SYNTHETIC DATA",
            "freshness": "DEMO",
        }
    ]
    from backend.app.intelligence.source_attribution import SourceAttributionEngine
    sources = SourceAttributionEngine().attribute_sources(
        spill_lat=spill_lat,
        spill_lon=spill_lon,
        spill_time=scene["acquisition_time"],
        vessels=vessels,
        infrastructure=infrastructure,
    )
    for src in sources:
        src["evidence"] = f"[DEMO / SYNTHETIC] {src.get('evidence', '')} Possible source requiring verification. Not a causal determination."
        src["data_source"] = "DEMO / SYNTHETIC DATA"
        
    forecast_bands = []
    
    active_track = None
    
    assets = []
    
    impacts = []
    
    recommendations = []
    
    return {
        "mode": "DEMO",
        "location": {"name": name, "latitude": lat, "longitude": lon, "bbox": bbox},
        "satellite": {
            "status": "DEMO",
            "message": "DEMO / SYNTHETIC DATA — not a Copernicus observation.",
            "products": [scene],
        },
        "spill_candidates": [
            {
                "detection_id": "DEMO-SPILL-1",
                "predicted_class": "oil_spill",
                "geom_geojson": spill_geom,
                "centroid_lat": spill_lat,
                "centroid_lon": spill_lon,
                "area_km2": 4.2,
                "perimeter_km": 12.0,
                "confidence": 0.62,
                "lookalike_risk_score": 0.35,
                "model_version": "DEMO synthetic generator",
                "morphology_features": {"circularity": 0.4, "is_elongated_plume": True, "pixel_count": 0},
                "created_at": scene["acquisition_time"],
                "data_status": "DEMO",
            }
        ],
        "vessels": {"status": "DEMO", "message": "DEMO / SYNTHETIC vessel positions.", "vessels": vessels},
        "infrastructure": {"status": "DEMO", "message": "DEMO / SYNTHETIC infrastructure.", "infrastructure": infrastructure},
        "possible_sources": sources,
        "forecast_bands": forecast_bands,
        "active_track": active_track,
        "assets": assets,
        "impacts": impacts,
        "recommendations": recommendations,
        "warnings": ["All objects in this result are DEMO / SYNTHETIC DATA."],
        "stage_status": {
            "geocoding": "OK",
            "satellite_search": "DEMO",
            "spill_processing": "DEMO",
            "vessels": "DEMO",
            "infrastructure": "DEMO",
            "attribution": "DEMO",
            "forecasting": "DEMO"
        },
    }


def _real_payload(lat: float, lon: float, name: str) -> Dict[str, Any]:
    bbox, aoi = aoi_from_point(lat, lon, 40.0)
    warnings: List[str] = []
    stage = {
        "geocoding": "OK",
        "satellite_search": "PENDING",
        "spill_processing": "SKIPPED",
        "vessels": "PENDING",
        "infrastructure": "PENDING",
        "attribution": "PENDING",
        "forecasting": "PENDING"
    }

    client = CDSEClient()
    products: List[Dict[str, Any]] = []
    sat_status = "UNAVAILABLE"
    sat_message = "REAL SATELLITE DATA TEMPORARILY UNAVAILABLE"
    if not client.has_credentials:
        sat_message = "REAL SATELLITE DATA TEMPORARILY UNAVAILABLE"
        stage["satellite_search"] = "UNAVAILABLE"
        warnings.append("Copernicus credentials are not available to the backend.")
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=14)
        result = client.search_sentinel1(bbox=bbox, start=start, end=end, max_records=8)
        if result.get("data_mode") == "UNAVAILABLE":
            sat_status = "UNAVAILABLE"
            sat_message = "REAL SATELLITE DATA TEMPORARILY UNAVAILABLE"
            stage["satellite_search"] = "UNAVAILABLE"
            warnings.append(result.get("message") or sat_message)
        elif not result.get("products"):
            sat_status = "EMPTY"
            sat_message = "NO REAL SENTINEL-1 DATA FOUND FOR THIS SEARCH"
            stage["satellite_search"] = "EMPTY"
        else:
            sat_status = "OK"
            sat_message = f"Found {len(result['products'])} real Sentinel-1 IW GRD product(s)."
            stage["satellite_search"] = "OK"
            for prod in result["products"]:
                products.append({
                    "scene_id": prod.get("id"),
                    "scene_name": prod.get("title"),
                    "source": "Copernicus Sentinel-1",
                    "sensor_mode": "IW",
                    "polarization": [p.strip() for p in str(prod.get("polarisation") or "VV,VH").split(",") if p.strip()],
                    "acquisition_time": prod.get("acquisition_time"),
                    "footprint_geojson": prod.get("footprint"),
                    "bbox": bbox,
                    "is_synthetic": False,
                    "ingestion_status": "CATALOGUE",
                    "product_id": prod.get("id"),
                    "title": prod.get("title"),
                    "polarisation": prod.get("polarisation"),
                    "product_type": prod.get("product_type"),
                    "s3_path": prod.get("s3_path"),
                    "data_status": "REAL",
                })

    from backend.app.services.ais_client import AISClient
    ais_res = AISClient().get_vessels_in_bbox(bbox[0], bbox[1], bbox[2], bbox[3])
    if ais_res.get("status") != "COMPLETED":
        stage["vessels"] = "UNAVAILABLE"
        warnings.append("LIVE VESSEL DATA UNAVAILABLE")
        vessels_block = {
            "status": "UNAVAILABLE",
            "message": "LIVE VESSEL DATA UNAVAILABLE",
            "vessels": [],
        }
    else:
        stage["vessels"] = "OK"
        vessels_block = {
            "status": "OK",
            "message": f"{len(ais_res.get('vessels') or [])} AIS vessel(s) returned.",
            "vessels": ais_res.get("vessels") or [],
        }

    from backend.app.services.infrastructure_client import InfrastructureClient
    infra_res = InfrastructureClient().get_infrastructure_in_bbox(bbox[0], bbox[1], bbox[2], bbox[3])
    if infra_res.get("status") != "COMPLETED":
        stage["infrastructure"] = "UNAVAILABLE"
        warnings.append("Pipeline/platform/port layer unavailable for this AOI.")
        infra_block = {
            "status": "UNAVAILABLE",
            "message": "Pipeline data unavailable for this AOI",
            "infrastructure": [],
        }
    else:
        items = infra_res.get("infrastructure") or []
        stage["infrastructure"] = "OK" if items else "EMPTY"
        infra_block = {
            "status": stage["infrastructure"],
            "message": (
                f"{len(items)} OpenStreetMap infrastructure feature(s)."
                if items
                else "No OSM port/platform/pipeline nodes found in this AOI. This is not proof that none exist."
            ),
            "infrastructure": items,
        }

    spill_candidates = []
    import os
    import numpy as np
    from PIL import Image

    if products:
        prod = products[0]
        # Download quicklook
        q_res = client.download_quicklook(prod["product_id"], prod["title"], "temp_downloads")
        if q_res.get("status") == "SUCCESS":
            local_path = q_res["local_path"]
            prod["quicklook_local"] = f"/static/images/{os.path.basename(local_path)}"
            
            try:
                # Read image and convert to grayscale numpy array
                img = Image.open(local_path).convert('L')
                arr = np.array(img, dtype=np.float32)
                
                # Run slick detection
                from backend.app.services.slick_detection_service import detect_dark_spot_candidates
                det_res = detect_dark_spot_candidates(arr, bbox)
                
                if det_res.get("candidates"):
                    stage["spill_processing"] = "OK"
                    spill_candidates = det_res["candidates"]
                else:
                    stage["spill_processing"] = "NO_CANDIDATE"
                    warnings.append(det_res.get("message", "No spill candidates detected."))
            except Exception as e:
                stage["spill_processing"] = "ERROR"
                warnings.append(f"Spill processing failed: {e}")
        else:
            stage["spill_processing"] = "UNAVAILABLE"
            warnings.append("Could not download satellite quicklook for processing.")
    else:
        stage["spill_processing"] = "SKIPPED"
        warnings.append("No satellite product to process.")

    from backend.app.intelligence.source_attribution import SourceAttributionEngine
    from backend.app.services.source_correlation_service import estimate_source_zone
    
    # Attribute based on best candidate or incident center
    s_lat, s_lon = lat, lon
    if spill_candidates:
        s_lat = spill_candidates[0].get("centroid_lat", lat)
        s_lon = spill_candidates[0].get("centroid_lon", lon)

    backtrack = estimate_source_zone(s_lat, s_lon)
    if backtrack["status"] == "COMPLETED":
        s_lat = backtrack["source_lat"]
        s_lon = backtrack["source_lon"]

    sources = SourceAttributionEngine().attribute_sources(
        spill_lat=s_lat,
        spill_lon=s_lon,
        spill_time=products[0].get("acquisition_time") if products else datetime.now(timezone.utc).isoformat(),
        vessels=vessels_block["vessels"],
        infrastructure=infra_block["infrastructure"],
    )
    for src in sources:
        src["explanation"] = (
            f"{src.get('explanation', '')} Spatially nearby association only. "
            "Possible source requiring verification — not a determination that this object caused a spill."
        )
    stage["attribution"] = "OK"

    # NEW: Defer forecast to intelligence endpoint
    forecast_bands = []
    assets = []
    impacts = []
    recommendations = []
    active_track = None
    stage["forecasting"] = "PENDING_INVESTIGATION"

    return {
        "mode": "REAL",
        "location": {"name": name, "latitude": lat, "longitude": lon, "bbox": bbox, "aoi_geojson": aoi},
        "satellite": {"status": sat_status, "message": sat_message, "products": products},
        "spill_candidates": spill_candidates,
        "vessels": vessels_block,
        "infrastructure": infra_block,
        "possible_sources": sources,
        "backtrack": backtrack,
        "weather": backtrack.get("weather", {}),
        "forecast_bands": forecast_bands,
        "active_track": active_track,
        "assets": assets,
        "impacts": impacts,
        "recommendations": recommendations,
        "warnings": warnings,
        "stage_status": stage,
    }


@router.get("/geocode")
def geocode_location(q: str = Query(..., min_length=1)):
    provider = NominatimGeocodingProvider()
    result = provider.geocode(q, radius_km=25.0)
    loc = result.get("location")
    status = result.get("status")
    if loc is None:
        return APIResponse(
            success=False,
            data={
                "status": getattr(status, "status", "EMPTY"),
                "message": getattr(status, "message", "Location not found."),
                "candidates": result.get("candidates") or [],
            },
        )
    return APIResponse(
        data={
            "name": loc.name,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "display_name": loc.display_name,
            "bbox": loc.bbox,
            "candidates": result.get("candidates") or [],
        }
    )


@router.post("/analyze")
def create_incident(data: IncidentCreate, db: Session = Depends(get_db)):
    incident = Incident(
        name=data.name,
        latitude=data.latitude,
        longitude=data.longitude,
        mode=data.mode,
        spill_type=data.spill_type,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    mode = (data.mode or "DEMO").upper()
    if mode in ("REAL", "REAL_DATA"):
        payload = _real_payload(data.latitude, data.longitude, data.name)
    else:
        payload = _demo_payload(data.latitude, data.longitude, data.name)

    payload["incident_id"] = incident.incident_id
    payload["incident"] = {
        "incident_id": incident.incident_id,
        "name": incident.name,
        "latitude": incident.latitude,
        "longitude": incident.longitude,
        "mode": incident.mode,
    }
    return APIResponse(data=payload)


@router.get("/")
def get_incidents(db: Session = Depends(get_db)):
    incidents = db.query(Incident).all()
    return APIResponse(data=[
        {
            "incident_id": i.incident_id,
            "name": i.name,
            "latitude": i.latitude,
            "longitude": i.longitude,
            "mode": i.mode,
            "timestamp": i.timestamp.isoformat() if i.timestamp else None,
        }
        for i in incidents
    ])


@router.get("/{incident_id}/intelligence")
def get_intelligence(incident_id: str, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    mode = (incident.mode or "DEMO").upper()
    if mode in ("REAL", "REAL_DATA"):
        payload = _real_payload(incident.latitude, incident.longitude, incident.name)
    else:
        payload = _demo_payload(incident.latitude, incident.longitude, incident.name)
    payload["incident_id"] = incident.incident_id
    return APIResponse(data=payload)
